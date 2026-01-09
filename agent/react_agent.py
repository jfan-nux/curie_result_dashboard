#!/usr/bin/env python3
"""
ReAct Agent for Experiment Callouts

A ReAct (Reason + Act) agent that analyzes experiments and generates daily callouts.
Uses Portkey/Claude for LLM and function calling for tool execution.

Architecture: See agent/ARCHITECTURE_DIAGRAMS.md for detailed flow diagrams.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from utils.logger import get_logger
from utils.snowflake_connection import SnowflakeHook
from agent.tools import (
    get_live_experiments,
    get_significant_metrics,
    get_all_metrics_for_analysis,
    parse_metric_spec,
    find_source_sql,
    get_experiment_brief,
    get_metric_definition,
    query_snowflake,
    get_tool_definitions,
    execute_tool
)

load_dotenv()
logger = get_logger(__name__)


# ========================================
# SYSTEM PROMPT & RULES
# ========================================

SYSTEM_PROMPT = """You are a senior experiment analysis data scientist for DoorDash. Your job is to deeply analyze experiments and generate insightful callouts.

## Your Task
Generate a thoughtful, analytical daily callout. Don't just report numbers - EXPLAIN what they mean and WHY they matter.

## Analysis Approach
For each experiment:
1. **Understand the feature first** - Use get_experiment_brief to understand what this feature does
2. **Check primary metrics** - These determine success/failure
3. **Check secondary metrics** - These provide supporting context
4. **Check guardrails** - ONLY report significant NEGATIVE (safety violations)
5. **Look for patterns** - Conflicting metrics? Unexpected directions? Large movements?
6. **Reason about causation** - WHY are metrics moving this way?

## Deep Dive Triggers (ALWAYS investigate if you see these)
- Impact > 5% (positive or negative)
- Conflicting patterns (e.g., conversion ↑ but MAU ↓)
- Unexpected direction (opposite of desired_direction)
- Guardrail violations

When triggered, use:
- get_experiment_brief: What is this feature trying to do?
- get_all_metrics_for_analysis: See the full picture
- get_metric_definition: How is this metric calculated?
- find_source_sql: What data sources are used?

## Critical Thinking Questions
When analyzing, ask yourself:
1. **What is the feature hypothesis?** (from brief_summary)
2. **Are the metrics supporting or contradicting the hypothesis?**
3. **If contradicting, what could explain it?**
   - Is this a tradeoff (quality vs quantity)?
   - Is this a segment effect (new vs existing users)?
   - Is this an unintended consequence?
4. **What would I recommend to the PM?**

## Multi-Arm Experiments (CRITICAL)
ALWAYS check the `variant_name` column in get_significant_metrics output.
- **SINGLE-ARM**: Only one treatment variant (e.g., "treatment", "treatment_group")
- **MULTI-ARM**: Multiple treatment variants (e.g., "twoweek" + "twentyone", or "treatment_address" + "treatment_cart")

**If you see 2+ distinct treatment variants (not counting "control"):**
1. YOU MUST use the MULTI-ARM format below
2. Report metrics separately BY ARM
3. Compare arms head-to-head on primary metrics
4. DECLARE A WINNING ARM (or state why no clear winner)

Example multi-arm variant_names you might see:
- "twoweek", "twentyone" (two treatment arms)
- "treatment_address", "treatment_cart" (two treatment arms)
- "arm_a", "arm_b", "arm_c" (three treatment arms)

## Output Format

### For SINGLE-ARM experiments:

### [Experiment Name](curie_ios_link)
**Feature:** [Brief description - explain what it does in plain English]
**Status:** [project_status] | **Rollout:** [rollout_pct]

**Primary Metrics:**
- [metric_name]: [impact]% (p=[p_value]) - [stat_sig]
  - *Interpretation: [What this means for the feature hypothesis]*

**Secondary Metrics:**
- [metric_name]: [impact]% (p=[p_value]) - [stat_sig]

**Guardrails:** (only if significant negative)
- [metric_name]: [impact]% (p=[p_value]) - ALERT
  - *Risk: [What this violation means]*

**Analysis:**
[Deep analysis of WHY the metrics show this pattern]

**Recommendation:**
[Specific, actionable recommendation]

---

### For MULTI-ARM experiments:

### [Experiment Name](curie_ios_link)
**Feature:** [Brief description]
**Status:** [project_status] | **Rollout:** [rollout_pct]
**Arms:** [List all treatment arms]

#### Arm Comparison

| Metric | [Arm 1] | [Arm 2] | [Arm 3 if exists] | Winner |
|--------|---------|---------|-------------------|--------|
| [primary_metric_1] | +X.X% (p=...) | +Y.Y% (p=...) | ... | [Arm name] |
| [primary_metric_2] | ... | ... | ... | [Arm name] |

#### By Arm Analysis:

**[Arm 1 Name]:**
- Primary: [metrics with impact and significance]
- Guardrails: [any violations]
- Summary: [1-2 sentence assessment]

**[Arm 2 Name]:**
- Primary: [metrics with impact and significance]
- Guardrails: [any violations]
- Summary: [1-2 sentence assessment]

**🏆 Winning Arm: [Arm Name]**
- Rationale: [Why this arm is recommended based on primary metrics, guardrails, and tradeoffs]
- Confidence: [High/Medium/Low]

**Recommendation:**
[Ship winning arm / Continue testing / Neither arm ready]

---

## Rules
- Use minimal emoji (max 3 total, except 🏆 for winning arm)
- Link experiment names to their Curie URL
- NEVER just report numbers without interpretation
- For multi-arm: ALWAYS declare a winner (or explain why no winner yet)
- If you see interesting patterns, INVESTIGATE with more tool calls
- Skip experiments with no significant metrics

## WebX Metric Rule (IMPORTANT)
When analyzing mWeb/web experiments that have webx_* metrics:
- **DO NOT** use consumers_mau or general order_rate_per_entity metrics as primary indicators
- **USE** webx_conversion_rate or webx_order_rate instead - these are more comprehensive for web funnels
- Reason: General consumer metrics (MAU, order_rate_per_entity) can be misleading for web experiments due to identity stitching issues between web and app
- webx_* metrics measure the full web visitor funnel correctly

## Available Tools
Use tools liberally to gather context before generating analysis."""


# ========================================
# REACT AGENT CLASS
# ========================================

class ExperimentCalloutAgent:
    """
    ReAct agent for generating experiment callouts.
    
    ReAct Pattern:
    1. REASON - LLM thinks about what to do next
    2. ACT - LLM calls a tool
    3. OBSERVE - Tool result added to context
    4. REPEAT until done or max iterations
    """
    
    # Agent configuration
    MAX_ITERATIONS = 20
    MAX_TOOL_CALLS = 30
    # Thinking models for deeper analysis:
    # - gpt-5.2: Latest thinking model (if available)
    # - o1-preview: OpenAI's reasoning model (best for complex analysis)
    # - o1-mini: Faster/cheaper reasoning model
    # - gpt-4o: Standard model (faster but less thoughtful)
    DEFAULT_MODEL = "gpt-5.2"
    
    def __init__(self, model: str = None, verbose: bool = False):
        """
        Initialize the ReAct agent.
        
        Args:
            model: LLM model to use (defaults to o1-preview for deeper analysis)
            verbose: If True, print context being sent to LLM
        """
        self.model = model or self.DEFAULT_MODEL
        self.verbose = verbose
        self.client = None
        self.tool_call_count = 0
        self.total_tool_calls = 0  # Track total across all iterations
        self.iteration_count = 0
        self.messages: List[Dict[str, Any]] = []
        
        self._initialize_client()
    
    @property
    def stats(self) -> dict:
        """Get agent statistics."""
        return {
            'model': self.model,
            'iterations': self.iteration_count,
            'tool_calls': self.total_tool_calls
        }
    
    def _initialize_client(self):
        """Initialize Portkey client via OpenAI SDK."""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not available. Please install: pip install openai")
            return
        
        try:
            portkey_api_key = os.getenv('PORTKEY_API_KEY')
            portkey_virtual_key = os.getenv('PORTKEY_OPENAI_VIRTUAL_KEY')
            
            if not all([portkey_api_key, portkey_virtual_key]):
                logger.error("Missing Portkey configuration. Set PORTKEY_API_KEY and PORTKEY_OPENAI_VIRTUAL_KEY")
                return
            
            base_url = os.getenv('PORTKEY_BASE_URL', 'https://api.portkey.ai/v1')
            
            self.client = openai.OpenAI(
                api_key="dummy",  # Required by SDK but ignored by Portkey
                base_url=base_url,
                default_headers={
                    "X-Portkey-API-Key": portkey_api_key,
                    "X-Portkey-Virtual-Key": portkey_virtual_key
                }
            )
            
            logger.info(f"Initialized Portkey client with model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Portkey client: {e}")
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for the LLM."""
        return get_tool_definitions()
    
    def _execute_tool_call(self, tool_call) -> str:
        """
        Execute a single tool call.
        
        Args:
            tool_call: OpenAI tool call object
            
        Returns:
            Tool execution result as string
        """
        self.tool_call_count += 1
        self.total_tool_calls += 1
        
        tool_name = tool_call.function.name
        arguments_str = tool_call.function.arguments
        
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse arguments for {tool_name}: {arguments_str}")
            return f"Error: Invalid arguments for {tool_name}"
        
        logger.info(f"Executing tool [{self.tool_call_count}]: {tool_name}({arguments})")
        
        try:
            result = execute_tool(tool_name, arguments)
            logger.info(f"Tool {tool_name} returned {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return f"Error executing {tool_name}: {str(e)}"
    
    def _call_llm(self) -> Any:
        """
        Call the LLM with current messages and tools.
        
        Returns:
            OpenAI ChatCompletion response
        """
        if not self.client:
            raise RuntimeError("Portkey client not initialized")
        
        # Verbose mode: show what context is being sent
        if self.verbose:
            self._print_context()
        
        # Thinking models (o1, gpt-5.x) don't support temperature or tool_choice
        is_thinking_model = self.model.startswith("o1") or self.model.startswith("gpt-5")
        
        if is_thinking_model:
            # Thinking models (o1, gpt-5.x) use different parameters
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self._get_tools(),
                max_completion_tokens=16000  # thinking models use max_completion_tokens
            )
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self._get_tools(),
                tool_choice="auto",
                max_tokens=4096,
                temperature=0.1
            )
        
        return response
    
    def _print_context(self):
        """Print the context being sent to the LLM (for debugging)."""
        print("\n" + "=" * 80)
        print("CONTEXT SENT TO LLM")
        print("=" * 80)
        
        total_chars = 0
        for i, msg in enumerate(self.messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            content_len = len(content) if content else 0
            total_chars += content_len
            
            if role == 'system':
                print(f"\n[{i}] SYSTEM PROMPT: {content_len} chars")
                print("-" * 40)
                print(content[:500] + "..." if len(content) > 500 else content)
            elif role == 'user':
                print(f"\n[{i}] USER: {content_len} chars")
                print("-" * 40)
                print(content[:300] + "..." if len(content) > 300 else content)
            elif role == 'assistant':
                tool_calls = msg.get('tool_calls', [])
                if tool_calls:
                    print(f"\n[{i}] ASSISTANT (tool calls): {len(tool_calls)} calls")
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            print(f"   - {tc.get('function', {}).get('name', 'unknown')}")
                else:
                    print(f"\n[{i}] ASSISTANT: {content_len} chars")
            elif role == 'tool':
                tool_id = msg.get('tool_call_id', 'unknown')
                print(f"\n[{i}] TOOL RESULT ({tool_id[:8]}...): {content_len} chars")
                # Show first 200 chars of tool result
                if content:
                    preview = content[:200].replace('\n', ' ')
                    print(f"   Preview: {preview}...")
        
        print("\n" + "-" * 40)
        print(f"TOTAL CONTEXT: {total_chars:,} chars ({len(self.messages)} messages)")
        print("=" * 80 + "\n")
    
    def _react_loop(self, user_prompt: str) -> str:
        """
        Execute the ReAct loop.
        
        Args:
            user_prompt: Initial user prompt
            
        Returns:
            Final agent response
        """
        # Initialize conversation
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        self.iteration_count = 0
        self.tool_call_count = 0
        
        while self.iteration_count < self.MAX_ITERATIONS:
            self.iteration_count += 1
            logger.info(f"=== ReAct Iteration {self.iteration_count}/{self.MAX_ITERATIONS} ===")
            
            # Check tool call limit
            if self.tool_call_count >= self.MAX_TOOL_CALLS:
                logger.warning(f"Max tool calls reached ({self.MAX_TOOL_CALLS})")
                break
            
            # 1. REASON + ACT: Call LLM
            try:
                response = self._call_llm()
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return f"Error: LLM call failed - {str(e)}"
            
            assistant_message = response.choices[0].message
            
            # Add assistant message to history
            self.messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in (assistant_message.tool_calls or [])
                ] if assistant_message.tool_calls else None
            })
            
            # Check if LLM wants to stop (no tool calls)
            if not assistant_message.tool_calls:
                logger.info("LLM finished (no more tool calls)")
                return assistant_message.content or "No response generated"
            
            # 2. OBSERVE: Execute tool calls
            for tool_call in assistant_message.tool_calls:
                result = self._execute_tool_call(tool_call)
                
                # Add tool result to messages
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        
        # Max iterations reached
        logger.warning(f"Max iterations reached ({self.MAX_ITERATIONS})")
        
        # Try to get a final response
        self.messages.append({
            "role": "user",
            "content": "Please provide your final callout based on the information gathered so far."
        })
        
        try:
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                max_tokens=4096,
                temperature=0.1
            )
            return final_response.choices[0].message.content or "No response generated"
        except Exception as e:
            return f"Error getting final response: {str(e)}"
    
    def generate_callout(self, date: str = None) -> str:
        """
        Generate daily experiment callout.
        
        Args:
            date: Date to analyze (defaults to today)
            
        Returns:
            Markdown formatted callout
        """
        if not self.client:
            return "Error: Portkey client not initialized. Check your environment variables."
        
        date = date or datetime.now().date().isoformat()
        
        user_prompt = f"""Generate the daily experiment callout for {date}.

Steps:
1. Get the list of live experiments
2. For each experiment with an analysis_id, check for significant metrics
3. Prioritize: primary metrics > secondary > guardrails
4. If you see conflicting patterns or large movements, investigate why
5. Generate a concise callout for the team

Focus on actionable insights. Skip experiments with no significant movements."""
        
        logger.info(f"Starting callout generation for {date}")
        start_time = datetime.now()
        
        result = self._react_loop(user_prompt)
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Callout generation completed in {duration:.1f}s")
        logger.info(f"Stats: {self.iteration_count} iterations, {self.tool_call_count} tool calls")
        
        return result
    
    def analyze_experiment(self, project_name: str, analysis_id: str) -> str:
        """
        Analyze a specific experiment.
        
        Args:
            project_name: Experiment name
            analysis_id: Curie analysis ID
            
        Returns:
            Detailed analysis
        """
        if not self.client:
            return "Error: Portkey client not initialized."
        
        user_prompt = f"""Analyze the experiment "{project_name}" (analysis_id: {analysis_id}).

1. Get the experiment brief to understand the feature
2. Get all significant metrics
3. If you see conflicting patterns, investigate why
4. Provide a detailed analysis with recommendations

Be thorough but concise."""
        
        logger.info(f"Starting analysis for {project_name}")
        return self._react_loop(user_prompt)
    
    def is_available(self) -> bool:
        """Check if agent is ready to use."""
        return self.client is not None


# ========================================
# UTILITY FUNCTIONS
# ========================================

def get_most_recent_date() -> str:
    """
    Get the most recent date with experiment data in Snowflake.
    
    Returns:
        Date string in YYYY-MM-DD format
    """
    from utils.snowflake_connection import SnowflakeHook
    
    query = """
    SELECT MAX(DATE(fetched_at)) as latest_date
    FROM proddb.fionafan.coda_experiments_focused
    WHERE view_name = 'Live Experiments'
    """
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty or df.iloc[0]['latest_date'] is None:
                # Fallback to today
                return datetime.now().date().isoformat()
            
            latest_date = df.iloc[0]['latest_date']
            
            # Handle different date formats
            if hasattr(latest_date, 'isoformat'):
                return latest_date.isoformat()
            return str(latest_date)[:10]
            
    except Exception as e:
        logger.warning(f"Could not get most recent date: {e}. Using today.")
        return datetime.now().date().isoformat()


def get_output_path(date: str) -> str:
    """
    Generate output file path for callout.
    
    Args:
        date: Date being analyzed (YYYY-MM-DD)
        
    Returns:
        Path like: agent/agent_callout/agent_callout_0106_143052.md
    """
    from pathlib import Path
    
    # Create output directory
    output_dir = Path(__file__).parent / "agent_callout"
    output_dir.mkdir(exist_ok=True)
    
    # Format: MMDD from date, HHMMSS from current time
    date_part = date[5:7] + date[8:10]  # Extract MMDD
    time_part = datetime.now().strftime("%H%M%S")
    
    filename = f"agent_callout_{date_part}_{time_part}.md"
    
    return str(output_dir / filename)


def format_for_slack(callout: str, date: str) -> str:
    """
    Convert markdown callout to Slack mrkdwn format.
    
    Args:
        callout: Markdown callout text
        date: Date of the callout
        
    Returns:
        Slack-formatted string
    """
    import re
    
    # Slack mrkdwn conversions
    slack_text = callout
    
    # Convert markdown links [text](url) to Slack <url|text>
    slack_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', slack_text)
    
    # Convert **bold** to *bold*
    slack_text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', slack_text)
    
    # Convert ### headers to *bold* with emoji
    slack_text = re.sub(r'^### (.+)$', r'*\1*', slack_text, flags=re.MULTILINE)
    
    # Convert horizontal rules
    slack_text = re.sub(r'^---+$', r'───────────────────', slack_text, flags=re.MULTILINE)
    
    # Convert tables to code blocks (Slack doesn't support tables well)
    # Simple approach: wrap tables in ``` 
    lines = slack_text.split('\n')
    in_table = False
    result_lines = []
    for line in lines:
        if line.strip().startswith('|') and not in_table:
            result_lines.append('```')
            in_table = True
        elif not line.strip().startswith('|') and in_table:
            result_lines.append('```')
            in_table = False
        result_lines.append(line)
    if in_table:
        result_lines.append('```')
    
    slack_text = '\n'.join(result_lines)
    
    # Add header
    header = f"📊 *NUX Experiment Callout - {date}*\n\n"
    
    return header + slack_text


def persist_callout_to_snowflake(
    callout_date: str,
    full_callout: str,
    slack_formatted: str,
    model_used: str,
    generation_time_seconds: float,
    tool_calls_count: int
) -> bool:
    """
    Persist callout to Snowflake table.
    
    Creates table if it doesn't exist, otherwise appends.
    
    Args:
        callout_date: Date analyzed
        full_callout: Full markdown callout
        slack_formatted: Slack mrkdwn formatted callout
        model_used: LLM model used
        generation_time_seconds: Time taken to generate
        tool_calls_count: Number of tool calls made
        
    Returns:
        True if successful
    """
    import pandas as pd
    
    DATABASE = "proddb"
    SCHEMA = "fionafan"
    TABLE = "nux_experiment_callouts"
    
    try:
        with SnowflakeHook(database=DATABASE, schema=SCHEMA, create_local_spark=False) as hook:
            # Check if table exists
            check_query = f"""
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = '{SCHEMA.upper()}' 
            AND table_name = '{TABLE.upper()}'
            AND table_catalog = '{DATABASE.upper()}'
            """
            result = hook.query_snowflake(check_query, method='pandas')
            table_exists = result.iloc[0]['cnt'] > 0
            
            if not table_exists:
                # Create table
                create_query = f"""
                CREATE TABLE {DATABASE}.{SCHEMA}.{TABLE} (
                    callout_id VARCHAR(36) DEFAULT UUID_STRING(),
                    callout_date DATE NOT NULL,
                    full_callout TEXT,
                    slack_formatted TEXT,
                    model_used VARCHAR(50),
                    generation_time_seconds FLOAT,
                    tool_calls_count INT,
                    generated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
                """
                hook.query_without_result(create_query)
                logger.info(f"Created table {DATABASE}.{SCHEMA}.{TABLE}")
            
            # Check if callout for this date already exists
            check_date_query = f"""
            SELECT COUNT(*) as cnt
            FROM {DATABASE}.{SCHEMA}.{TABLE}
            WHERE callout_date = '{callout_date}'
            """
            result = hook.query_snowflake(check_date_query, method='pandas')
            date_exists = result.iloc[0]['cnt'] > 0
            
            if date_exists:
                # Delete existing callout for this date (replace)
                delete_query = f"""
                DELETE FROM {DATABASE}.{SCHEMA}.{TABLE}
                WHERE callout_date = '{callout_date}'
                """
                hook.query_without_result(delete_query)
                logger.info(f"Replaced existing callout for {callout_date}")
            
            # Insert new callout
            # Escape single quotes in text
            full_callout_escaped = full_callout.replace("'", "''")
            slack_formatted_escaped = slack_formatted.replace("'", "''")
            
            insert_query = f"""
            INSERT INTO {DATABASE}.{SCHEMA}.{TABLE} 
            (callout_date, full_callout, slack_formatted, model_used, generation_time_seconds, tool_calls_count)
            VALUES (
                '{callout_date}',
                '{full_callout_escaped}',
                '{slack_formatted_escaped}',
                '{model_used}',
                {generation_time_seconds},
                {tool_calls_count}
            )
            """
            hook.query_without_result(insert_query)
            logger.info(f"Persisted callout to {DATABASE}.{SCHEMA}.{TABLE}")
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to persist callout to Snowflake: {e}")
        return False


# ========================================
# MAIN ENTRY POINT
# ========================================

def run_daily_callout(date: str = None, model: str = None, save: bool = True, 
                       verbose: bool = False, persist_to_snowflake: bool = True) -> tuple:
    """
    Run the daily callout generation.
    
    Args:
        date: Date to analyze (defaults to most recent with data)
        model: LLM model to use
        save: Whether to save output to file
        verbose: If True, print context being sent to LLM
        persist_to_snowflake: Whether to persist callout to Snowflake table
        
    Returns:
        Tuple of (callout_text, output_path or None)
    """
    import time
    
    # Get most recent date if not specified
    if date is None:
        date = get_most_recent_date()
        logger.info(f"Using most recent date with data: {date}")
    
    agent = ExperimentCalloutAgent(model=model, verbose=verbose)
    
    if not agent.is_available():
        return "Error: Agent not available. Check Portkey configuration.", None
    
    # Track generation time
    start_time = time.time()
    callout = agent.generate_callout(date=date)
    generation_time = time.time() - start_time
    
    # Get stats from agent
    tool_calls_count = getattr(agent, 'total_tool_calls', 0)
    model_used = agent.model
    
    output_path = None
    if save:
        output_path = get_output_path(date)
        with open(output_path, 'w') as f:
            f.write(f"# Experiment Callout - {date}\n\n")
            f.write(f"*Generated: {datetime.now().isoformat()}*\n\n")
            f.write("---\n\n")
            f.write(callout)
        logger.info(f"Callout saved to: {output_path}")
    
    # Persist to Snowflake
    if persist_to_snowflake:
        slack_formatted = format_for_slack(callout, date)
        persist_callout_to_snowflake(
            callout_date=date,
            full_callout=callout,
            slack_formatted=slack_formatted,
            model_used=model_used,
            generation_time_seconds=generation_time,
            tool_calls_count=tool_calls_count
        )
    
    return callout, output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate experiment callouts')
    parser.add_argument('--date', type=str, default=None, 
                        help='Date to analyze (YYYY-MM-DD). Defaults to most recent date with data.')
    parser.add_argument('--model', type=str, default=None, 
                        help='LLM model (default: gpt-5.2). Options: gpt-5.2, o1-preview, o1-mini, gpt-4o')
    parser.add_argument('--no-save', action='store_true', help='Do not save output to file')
    parser.add_argument('--verbose', '-v', action='store_true', 
                        help='Show context being sent to LLM')
    parser.add_argument('--fast', action='store_true',
                        help='Use gpt-4o for faster (but less thoughtful) analysis')
    
    args = parser.parse_args()
    
    # Fast mode uses gpt-4o
    model = args.model
    if args.fast and not model:
        model = "gpt-4o"
    
    print("=" * 80)
    print("EXPERIMENT CALLOUT AGENT")
    print(f"Model: {model or ExperimentCalloutAgent.DEFAULT_MODEL}")
    print("=" * 80)
    
    callout, output_path = run_daily_callout(
        date=args.date, 
        model=model,
        save=not args.no_save,
        verbose=args.verbose
    )
    
    print("\n" + callout)
    
    if output_path:
        print(f"\n{'=' * 80}")
        print(f"Callout saved to: {output_path}")
        print("=" * 80)

