# ReAct Agent Implementation Summary

## 📁 What Was Created

```
agent/
├── experiment_callout_agent.py    # Main ReAct agent (420 lines)
├── EXAMPLE_OUTPUT.md              # Sample output walkthrough
├── REACT_IMPLEMENTATION_GUIDE.md  # Technical details
├── QUICK_START.md                 # Quick reference
└── README.md                      # This file

run_callout_agent.py               # Runner script
```

---

## 🎯 Complete ReAct Implementation

### 1. Define Tools (What the agent can do)

```python
tools = [
    {
        "name": "get_live_experiments",
        "description": "Get all live experiments from Coda table",
        "parameters": {"date": "string (optional)"}
    },
    {
        "name": "get_significant_metrics",
        "description": "Get significant metrics for an experiment",
        "parameters": {
            "analysis_id": "string (required)",
            "metric_type": "primary|secondary|guardrail (optional)"
        }
    },
    {
        "name": "parse_metric_spec",
        "description": "Parse metric spec to understand composition",
        "parameters": {"spec_json": "string (required)"}
    },
    {
        "name": "find_source_sql",
        "description": "Find source SQL for a measure",
        "parameters": {"measure_id": "string (required)"}
    },
    {
        "name": "query_snowflake",
        "description": "Execute custom SQL query",
        "parameters": {"query": "string (required)"}
    }
]
```

### 2. Implement Tools (Actual Python functions)

```python
def get_live_experiments(self, date: str = None) -> str:
    """Execute SQL and return markdown table."""
    query = f"""
    SELECT project_name, brief_summary, curie_ios
    FROM proddb.fionafan.coda_experiments_focused
    WHERE view_name = 'Live Experiments'
      AND DATE(fetched_at) = '{date}'
    """
    # Execute and return as markdown
```

### 3. The ReAct Loop

```python
def run(self, task: str) -> str:
    messages = [system_prompt, user_task]
    
    for iteration in range(20):
        # Call LLM with tools
        response = portkey.chat(messages, tools=tools)
        
        if response.wants_tool:
            # Execute tools
            for tool_call in response.tool_calls:
                result = self.execute_tool(tool_call)
                messages.append({"role": "tool", "content": result})
        else:
            # Done!
            return response.content
```

### 4. Tool Router

```python
def execute_tool(self, tool_name: str, args: dict) -> str:
    """Route tool calls to implementations."""
    if tool_name == "get_live_experiments":
        return self.get_live_experiments(args.get('date'))
    elif tool_name == "get_significant_metrics":
        return self.get_significant_metrics(args['analysis_id'], args.get('metric_type'))
    # ... etc
```

---

## 🧠 How Rules Are Incorporated

### In System Prompt (Soft Rules):
```
STRICT ANALYSIS RULES:

1. Metric Priority:
   a) Primary metrics first
   b) Then secondary
   c) Finally guardrails

2. Guardrail Rules:
   - ONLY flag if stat_sig = 'significant negative'

3. Deep Dive Triggers:
   - Parse metric_spec ONLY if abs(impact) > 5%
```

### In Tool Code (Hard Rules):
```python
def get_significant_metrics(self, analysis_id, metric_type):
    # RULE: Guardrails only show negative
    if metric_type == 'guardrail':
        filter = "stat_sig = 'significant negative'"
    else:
        filter = "stat_sig IN ('sig positive', 'sig negative')"
    
    # RULE: Overall dimension first
    query += "ORDER BY CASE WHEN dimension='overall' THEN 0 ELSE 1 END"
```

### In Validation (Enforcement):
```python
def _validate_output(self, output: str) -> bool:
    # RULE: Check emoji count
    if emoji_count > max_allowed:
        return False
    
    # RULE: Must have recommendations
    if 'Recommendation' not in output:
        return False
```

---

## 🎬 Example Execution Trace

```
User: "Generate daily callout for all live experiments"

Iteration 1:
  🧠 "I need to get live experiments first"
  🔧 get_live_experiments(date="2026-01-06")
  👁️ "Found 5 experiments"

Iteration 2:
  🧠 "Check Block bad address experiment for primary metrics"
  🔧 get_significant_metrics("944d4986...", "primary")
  👁️ "checkout_conversion: +4.21% (p=0.003)"

Iteration 3:
  🧠 "Found significant primary! Check secondary"
  🔧 get_significant_metrics("944d4986...", "secondary")
  👁️ "cart_abandonment_rate: -3.12% (p=0.012)"

Iteration 4:
  🧠 "Check guardrails"
  🔧 get_significant_metrics("944d4986...", "guardrail")
  👁️ "No guardrail issues"

Iteration 5:
  🧠 "Large impact (+4.21%), let me see dimensional breakdown"
  🔧 query_snowflake("SELECT ... WHERE metric_name='checkout_conversion'...")
  👁️ "iOS: +5.9%, Android: +2.9%, New customers: +6.8%"

Iterations 6-15:
  [Analyzes remaining 4 experiments...]

Iteration 16:
  🧠 "I've analyzed all experiments. Generate callout."
  ✅ FINISH
```

---

## 📝 Output Format

The agent produces markdown like this:

```markdown
# Daily Experiment Callout - [Date]

## Summary
X experiments monitored
Y require attention

## [Experiment Name]

**Status:** [Flag type]
**Feature:** [brief_summary]

### Significant Metrics
- Primary: [metric] +X% (p=0.XX) [significance]
- Secondary: [metric] +Y% (p=0.YY) [significance]
- Guardrails: [status]

### Recommendation
[Action item]

---

[Next experiment...]
```

---

## 🔧 How to Run

### Option 1: Command Line
```bash
python run_callout_agent.py
```

### Option 2: Python Script
```python
from agent import ExperimentCalloutAgent

agent = ExperimentCalloutAgent()
result = agent.run("Generate daily callout for all live experiments")
print(result)
```

### Option 3: Scheduled (Databricks/Airflow)
```python
# In Databricks notebook or Airflow task
from agent import ExperimentCalloutAgent

agent = ExperimentCalloutAgent()
callout = agent.run(f"Generate callout for {today}")

# Post to Slack
post_to_slack(callout, channel="#nux-experiments")
```

---

## 🎨 Customization

### Change Task Prompt:
```python
task = """
Generate callout focusing ONLY on guardrail violations.
Skip experiments with no guardrail issues.
"""
```

### Adjust Rules:
```python
ExperimentCalloutAgent.RULES = {
    'large_impact_threshold': 0.03,  # Lower to 3%
    'max_emojis_per_callout': 1,     # Even more strict
}
```

### Add New Tool:
```python
# 1. Define in tools list
{
    "name": "get_historical_trend",
    "description": "Compare to last week's metrics",
    "parameters": {...}
}

# 2. Implement function
def get_historical_trend(self, analysis_id, metric_name):
    # SQL to compare week-over-week
    
# 3. Add to router
elif tool_name == "get_historical_trend":
    return self.get_historical_trend(args['analysis_id'], args['metric_name'])
```

---

## ✅ Key Advantages of This Approach

1. **Adaptive:** Agent decides which tools to use based on findings
2. **Efficient:** Doesn't waste time on flat experiments
3. **Transparent:** Can see reasoning at each step (in logs)
4. **Maintainable:** Rules in one place, easy to update
5. **Portable:** Works in notebooks, scripts, or scheduled jobs
6. **No MCP needed:** Pure Python + Portkey

---

## 🐛 Troubleshooting

### Agent makes too many tool calls:
→ Reduce `max_iterations` or add more specific instructions in prompt

### Output doesn't follow format:
→ Add output validation and provide example in system prompt

### Agent doesn't use tools properly:
→ Improve tool descriptions with examples
→ Add validation in execute_tool()

### Want to see thinking process:
→ Set `verbose=True` and check logs
→ Print messages after each iteration

---

## 📚 Documentation

- **EXAMPLE_OUTPUT.md** - See what output looks like
- **REACT_IMPLEMENTATION_GUIDE.md** - Technical deep dive  
- **QUICK_START.md** - Quick reference

---

**Ready to run with real data!** 🚀

The agent is fully functional and will work with your:
- `proddb.fionafan.coda_experiments_focused` (with brief_summary column)
- `proddb.fionafan.nux_curie_result_daily`
- Portkey configuration

