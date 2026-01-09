#!/usr/bin/env python3
"""
ReAct Agent Tools for Experiment Analysis

All tools the agent can use to analyze experiments and generate callouts.
Each tool is a Python function that returns a string (for LLM consumption).
"""

import json
import re
from datetime import datetime
from typing import Optional
from utils.snowflake_connection import SnowflakeHook
from utils.logger import get_logger

logger = get_logger(__name__)


# ========================================
# METRIC TYPE CLASSIFICATION
# ========================================

# SQL CASE statement for metric type classification
METRIC_TYPE_CASE = """
    CASE
        -- PRIMARY metrics
        WHEN metric_name IN (
            'cng_order_rate_nc',
            'consumer_order_frequency_l_28_d',
            'consumers_mau',
            'dashpass_signup',
            'dsmp_gov',
            'dsmp_order_frequency_7d',
            'dsmp_order_rate',
            'dsmp_order_rate_14d',
            'dsmp_order_rate_7d',
            'gov_per_order_curie',
            'nv_mau',
            'order_frequency_per_entity_7d',
            'order_rate_per_entity',
            'order_rate_per_entity_7d',
            'variable_profit_per_order',
            'webx_conversion_rate',
            'webx_order_rate'
        ) THEN 'primary'

        -- GUARDRAIL metrics
        WHEN metric_name IN (
            'ads_promotion_promotion_cx_discount',
            'ads_revenue',
            'consumer_mto',
            'core_quality_aotw',
            'core_quality_asap',
            'core_quality_botw',
            'core_quality_cancellation',
            'core_quality_late20',
            'core_quality_otw',
            'cx_app_quality_action_load_latency_android',
            'cx_app_quality_action_load_latency_ios',
            'cx_app_quality_action_load_latency_web',
            'cx_app_quality_crash_android',
            'cx_app_quality_crash_ios',
            'cx_app_quality_crash_web',
            'cx_app_quality_hitch_android',
            'cx_app_quality_hitch_ios',
            'cx_app_quality_inp_web',
            'cx_app_quality_page_action_error_android',
            'cx_app_quality_page_action_error_ios',
            'cx_app_quality_page_action_error_web',
            'cx_app_quality_page_load_error_android',
            'cx_app_quality_page_load_error_ios',
            'cx_app_quality_page_load_error_web',
            'cx_app_quality_page_load_latency_android',
            'cx_app_quality_page_load_latency_ios',
            'cx_app_quality_page_load_latency_web',
            'cx_app_quality_single_metric_ios',
            'cx_app_quality_tbt_web',
            'ox_subtotal_combined'
        ) THEN 'guardrail'

        -- Everything else is secondary
        ELSE 'secondary'
    END AS metric_type
"""


# ========================================
# DATA ACCESS TOOLS
# ========================================

def get_live_experiments(date: str = None) -> str:
    """
    Get all live experiments from Coda table.
    
    Args:
        date: Date in YYYY-MM-DD format (defaults to today)
        
    Returns:
        Markdown table with experiment details
    """
    date = date or datetime.now().date().isoformat()
    
    logger.info(f"Getting live experiments for {date}")
    
    query = f"""
    SELECT 
        project_name,
        brief_summary,
        details,
        status_notes,
        brief as brief_doc_link,
        curie_ios,
        curie_android,
        project_status,
        rollout_pct,
        updated_at
    FROM proddb.fionafan.coda_experiments_focused
    WHERE view_name = 'Live Experiments'
      AND DATE(fetched_at) = '{date}'
    ORDER BY project_name
    """
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty:
                return f"No live experiments found for {date}"
            
            # Extract analysis IDs from Curie links
            def extract_analysis_id(curie_link):
                if not curie_link or str(curie_link) == 'None':
                    return None
                match = re.search(r'analysisId=([a-f0-9\-]+)', str(curie_link), re.IGNORECASE)
                if match:
                    return match.group(1)
                match = re.search(r'/analysis/([a-f0-9\-]+)', str(curie_link))
                if match:
                    return match.group(1)
                return None
            
            df['analysis_id'] = df['curie_ios'].apply(extract_analysis_id)
            
            logger.info(f"Found {len(df)} live experiments")
            return df.to_markdown(index=False)
    
    except Exception as e:
        logger.error(f"Error getting live experiments: {e}")
        return f"Error: {str(e)}"


def get_significant_metrics(analysis_id: str, metric_type: str = None) -> str:
    """
    Get significant metrics for an experiment.
    
    Args:
        analysis_id: Curie analysis ID (UUID)
        metric_type: Filter by "primary", "secondary", or "guardrail" (optional)
        
    Returns:
        Markdown table with significant metrics
        
    Note: 
        - For guardrails, ONLY significant NEGATIVE metrics are returned (safety violations)
        - Primary/secondary show both positive and negative significant metrics
    """
    logger.info(f"Getting significant metrics for {analysis_id}, type={metric_type}")
    
    # Build metric type filter
    if metric_type:
        type_filter = f"AND metric_type = '{metric_type}'"
        # RULE: Guardrails only show significant negative
        if metric_type == "guardrail":
            stat_sig_filter = "AND stat_sig = 'significant negative'"
        else:
            stat_sig_filter = "AND stat_sig IN ('significant positive', 'significant negative')"
    else:
        type_filter = ""
        stat_sig_filter = "AND stat_sig IN ('significant positive', 'significant negative')"
    
    query = f"""
    WITH metrics_typed AS (
        SELECT 
            metric_name,
            dimension_name,
            dimension_cut_name,
            variant_name,
            metric_value,
            metric_impact_relative,
            p_value,
            stat_sig,
            metric_definition,
            metric_spec,
            metric_desired_direction,
            {METRIC_TYPE_CASE}
        FROM proddb.fionafan.nux_curie_result_daily
        WHERE analysis_id = '{analysis_id}'
          AND LOWER(variant_name) <> 'control'
    )
    SELECT 
        metric_type,
        metric_name,
        dimension_name,
        dimension_cut_name,
        variant_name,
        metric_value,
        metric_impact_relative,
        p_value,
        stat_sig,
        metric_definition,
        metric_desired_direction
    FROM metrics_typed
    WHERE 1=1
      {stat_sig_filter}
      {type_filter}
    ORDER BY 
        CASE metric_type WHEN 'primary' THEN 1 WHEN 'secondary' THEN 2 WHEN 'guardrail' THEN 3 END,
        CASE WHEN dimension_cut_name = 'overall' THEN 0 ELSE 1 END,
        ABS(metric_impact_relative) DESC
    LIMIT 50
    """
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty:
                type_msg = f" ({metric_type})" if metric_type else ""
                return f"No significant metrics found{type_msg}"
            
            logger.info(f"Found {len(df)} significant metrics")
            return df.to_markdown(index=False)
    
    except Exception as e:
        logger.error(f"Error getting significant metrics: {e}")
        return f"Error: {str(e)}"


def get_all_metrics_for_analysis(analysis_id: str, dimension_cut: str = "overall") -> str:
    """
    Get ALL metrics (including non-significant) for an analysis.
    
    Sorted by metric_type (primary > secondary > guardrail) then by impact magnitude.
    Helps identify:
    - Metrics moving together (correlated)
    - Tradeoff patterns (one up, one down)
    - Supporting/conflicting evidence
    
    Args:
        analysis_id: Curie analysis ID
        dimension_cut: Specific dimension cut (default: overall)
        
    Returns:
        Markdown table with all metrics sorted by type and impact magnitude
    """
    logger.info(f"Getting all metrics for {analysis_id}, dimension={dimension_cut}")
    
    query = f"""
    WITH metrics_typed AS (
        SELECT 
            metric_name,
            dimension_cut_name,
            variant_name,
            metric_value,
            metric_impact_relative,
            p_value,
            stat_sig,
            metric_definition,
            metric_desired_direction,
            {METRIC_TYPE_CASE}
        FROM proddb.fionafan.nux_curie_result_daily
        WHERE analysis_id = '{analysis_id}'
          AND dimension_cut_name = '{dimension_cut}'
          AND LOWER(variant_name) <> 'control'
    )
    SELECT 
        metric_type,
        metric_name,
        dimension_cut_name,
        variant_name,
        metric_value,
        metric_impact_relative,
        p_value,
        stat_sig,
        metric_definition,
        metric_desired_direction
    FROM metrics_typed
    ORDER BY 
        CASE metric_type WHEN 'primary' THEN 1 WHEN 'secondary' THEN 2 WHEN 'guardrail' THEN 3 END,
        ABS(metric_impact_relative) DESC NULLS LAST,
        metric_name,
        variant_name
    LIMIT 100
    """
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty:
                return f"No metrics found for analysis {analysis_id}"
            
            logger.info(f"Found {len(df)} total metrics")
            return df.to_markdown(index=False)
    
    except Exception as e:
        logger.error(f"Error getting all metrics: {e}")
        return f"Error: {str(e)}"


def query_snowflake(query: str) -> str:
    """
    Execute a custom Snowflake SQL query.
    
    Args:
        query: SQL query to execute
        
    Returns:
        Markdown table with results
    """
    logger.info(f"Executing custom query: {query[:100]}...")
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty:
                return "Query returned no results"
            
            logger.info(f"Query returned {len(df)} rows")
            return df.to_markdown(index=False)
    
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return f"Error: {str(e)}"


# ========================================
# ANALYSIS & REFLECTION TOOLS
# ========================================

def parse_metric_spec(spec_json: str) -> str:
    """
    Parse metric_spec JSON to understand metric composition.
    
    Args:
        spec_json: Metric spec JSON string
        
    Returns:
        Formatted text with metric composition details
    """
    logger.info("Parsing metric spec")
    
    try:
        spec = json.loads(spec_json)
        
        result = {
            "metric_type": spec.get("type"),
            "measures": []
        }
        
        # Parse SIMPLE metric
        if spec.get("type") == "METRIC_TYPE_SIMPLE":
            simple_param = spec.get("simpleParam", {})
            measure = simple_param.get("measure", {})
            
            result["measures"].append({
                "role": "value",
                "id": measure.get("id"),
                "name": measure.get("name"),
                "source_id": measure.get("sourceId"),
                "aggregation": simple_param.get("aggregation")
            })
        
        # Parse RATIO metric
        elif spec.get("type") == "METRIC_TYPE_RATIO":
            ratio_param = spec.get("ratioParam", {})
            
            # Numerator
            num_measure = ratio_param.get("numeratorMeasure", {})
            if num_measure:
                result["measures"].append({
                    "role": "numerator",
                    "id": num_measure.get("id"),
                    "name": num_measure.get("name"),
                    "source_id": num_measure.get("sourceId"),
                    "aggregation": ratio_param.get("numeratorAggregation")
                })
            
            # Denominator
            den_measure = ratio_param.get("denominatorMeasure", {})
            if den_measure:
                result["measures"].append({
                    "role": "denominator",
                    "id": den_measure.get("id"),
                    "name": den_measure.get("name"),
                    "source_id": den_measure.get("sourceId"),
                    "aggregation": ratio_param.get("denominatorAggregation")
                })
        
        # Parse FUNNEL metric
        elif spec.get("type") == "METRIC_TYPE_FUNNEL":
            funnel_param = spec.get("funnelParam", {})
            steps = funnel_param.get("steps", [])
            
            for i, step in enumerate(steps):
                measure = step.get("measure", {})
                result["measures"].append({
                    "role": f"step_{i+1}",
                    "id": measure.get("id"),
                    "name": measure.get("name"),
                    "source_id": measure.get("sourceId")
                })
        
        logger.info(f"Parsed {spec.get('type')} with {len(result['measures'])} measures")
        return json.dumps(result, indent=2)
    
    except Exception as e:
        logger.error(f"Error parsing metric spec: {e}")
        return f"Error parsing metric spec: {str(e)}"


def find_source_sql(measure_id: str) -> str:
    """
    Find source SQL definition for a measure.
    
    Args:
        measure_id: Measure UUID from metric_spec
        
    Returns:
        Formatted text with source details and SQL
    """
    logger.info(f"Finding source SQL for measure {measure_id}")
    
    query = f"""
    SELECT 
        id,
        name,
        description,
        compute_spec:lookBackPeriod as lookback_period,
        compute_spec:lookBackUnit as lookback_unit,
        compute_spec:snowflakeSpec:sql as sql,
        'https://ops.doordash.team/decision-systems/unified-metrics-platform/sources/'||id as url
    FROM CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_SOURCE
    WHERE id = '{measure_id}'
    """
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty:
                return f"No source found for measure ID: {measure_id}"
            
            row = df.iloc[0]
            
            # Format output
            output = f"""
**Source Name:** {row['name']}
**Description:** {row.get('description', 'N/A')}
**Lookback:** {row['lookback_period']} {row['lookback_unit']}
**URL:** {row['url']}

**SQL Definition:**
```sql
{row['sql']}
```
"""
            logger.info(f"Found source: {row['name']}")
            return output.strip()
    
    except Exception as e:
        logger.error(f"Error finding source SQL: {e}")
        return f"Error: {str(e)}"


# ========================================
# CONTEXT TOOLS
# ========================================

def get_experiment_brief(project_name: str, date: str = None) -> str:
    """
    Get experiment context and description.
    
    Args:
        project_name: Experiment project name
        date: Date (defaults to today)
        
    Returns:
        Formatted text with experiment context
    """
    date = date or datetime.now().date().isoformat()
    
    logger.info(f"Getting experiment brief for {project_name}")
    
    query = f"""
    SELECT 
        project_name,
        brief_summary,
        details,
        status_notes,
        brief as brief_doc_link,
        project_status,
        rollout_pct,
        curie_ios,
        updated_at
    FROM proddb.fionafan.coda_experiments_focused
    WHERE project_name = '{project_name}'
      AND view_name = 'Live Experiments'
      AND DATE(fetched_at) = '{date}'
    LIMIT 1
    """
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty:
                return f"Experiment '{project_name}' not found"
            
            row = df.iloc[0]
            
            status_notes = row.get('status_notes', '')
            status_notes_section = f"\n**Status Notes:**\n{status_notes}" if status_notes and str(status_notes) != 'None' else ""
            
            output = f"""
**Experiment:** {row['project_name']}
**Status:** {row['project_status']}
**Rollout:** {row.get('rollout_pct', 'N/A')}

**Feature Description:**
{row['brief_summary'] if row['brief_summary'] and str(row['brief_summary']) != 'None' else row.get('details', 'No description available')}
{status_notes_section}

**Brief Doc:** {row.get('brief_doc_link', 'Not available')}
**Curie Link:** {row['curie_ios']}
**Last Updated:** {row['updated_at']}
"""
            logger.info(f"Retrieved brief for {project_name}")
            return output.strip()
    
    except Exception as e:
        logger.error(f"Error getting experiment brief: {e}")
        return f"Error: {str(e)}"


def get_metric_definition(metric_name: str) -> str:
    """
    Get complete metric definition from TALLEYRAND_METRICS.
    
    Args:
        metric_name: Name of the metric
        
    Returns:
        Formatted text with metric definition and spec
    """
    logger.info(f"Getting metric definition for {metric_name}")
    
    query = f"""
    SELECT 
        name,
        description,
        metric_spec,
        desired_direction
    FROM CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_METRICS
    WHERE name = '{metric_name}'
    LIMIT 1
    """
    
    try:
        with SnowflakeHook(create_local_spark=False) as hook:
            df = hook.query_snowflake(query, method='pandas')
            
            if df.empty:
                return f"Metric definition not found for: {metric_name}"
            
            row = df.iloc[0]
            
            output = f"""
**Metric:** {row['name']}
**Description:** {row.get('description', 'N/A')}
**Desired Direction:** {row.get('desired_direction', 'N/A')}

**Specification:**
```json
{row['metric_spec']}
```
"""
            logger.info(f"Retrieved definition for {metric_name}")
            return output.strip()
    
    except Exception as e:
        logger.error(f"Error getting metric definition: {e}")
        return f"Error: {str(e)}"


# ========================================
# TOOL DEFINITIONS FOR LLM
# ========================================

def get_tool_definitions() -> list:
    """
    Get OpenAI-compatible tool definitions for all available tools.
    
    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_live_experiments",
                "description": """Get all live experiments from Coda experiments table.
                
                Returns experiment metadata including:
                - project_name: Experiment name
                - brief_summary: Feature description (concise)
                - details: Additional context
                - analysis_id: Curie analysis ID (extracted from curie_ios link)
                - project_status: Current status
                - rollout_pct: Rollout percentage""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (defaults to today)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_significant_metrics",
                "description": """Get significant metrics for a specific experiment.
                
                Returns metrics where stat_sig is 'significant positive' or 'significant negative'.
                Metrics are classified as: primary, secondary, or guardrail.
                
                IMPORTANT: For guardrails, ONLY 'significant negative' metrics are returned (safety violations).
                
                Results sorted by metric_type (primary > secondary > guardrail), then by impact magnitude.
                
                Recommended workflow:
                1. First call without metric_type to see all significant metrics
                2. Or filter by metric_type='primary' for main success metrics
                3. Then check metric_type='guardrail' for safety violations""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_id": {
                            "type": "string",
                            "description": "Curie analysis ID (UUID format)"
                        },
                        "metric_type": {
                            "type": "string",
                            "description": "Filter by metric type (optional). Guardrails only show significant negative.",
                            "enum": ["primary", "secondary", "guardrail"]
                        }
                    },
                    "required": ["analysis_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_all_metrics_for_analysis",
                "description": """Get ALL metrics (not just significant ones) for an experiment.
                
                Sorted by impact magnitude (largest movers first) to help identify:
                - Metrics moving together (correlated)
                - Tradeoff patterns (one up, one down)  
                - Supporting/conflicting evidence
                
                Use this when you need to see the complete picture:
                - After finding significant flags (for context)
                - To identify correlation patterns
                - To check if related metrics also moved
                
                Returns all metrics for a specific dimension cut (default: overall).""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_id": {
                            "type": "string",
                            "description": "Curie analysis ID"
                        },
                        "dimension_cut": {
                            "type": "string",
                            "description": "Dimension cut name (default: overall)"
                        }
                    },
                    "required": ["analysis_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "parse_metric_spec",
                "description": """Parse metric_spec JSON to understand metric composition.
                
                Returns:
                - Metric type (SIMPLE, RATIO, FUNNEL)
                - Component measures with IDs, names, and aggregations
                - Numerator/denominator for ratio metrics
                - Funnel steps for funnel metrics
                
                Use this when you need to understand HOW a metric is calculated.
                Measure IDs can be used with find_source_sql() to get data sources.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "spec_json": {
                            "type": "string",
                            "description": "Metric spec JSON string from metric_spec column"
                        }
                    },
                    "required": ["spec_json"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_source_sql",
                "description": """Find source SQL definition for a measure.
                
                Returns:
                - Source name
                - SQL definition (raw SQL code)
                - Lookback period (e.g., 30 days)
                - URL to ops.doordash.team
                
                Use this to understand:
                - What data tables are used
                - How the data is filtered/aggregated
                - Data freshness (lookback period)
                
                Particularly useful when metric behavior is unexpected.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "measure_id": {
                            "type": "string",
                            "description": "Measure UUID (from parse_metric_spec output)"
                        }
                    },
                    "required": ["measure_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_snowflake",
                "description": """Execute a custom Snowflake SQL query.
                
                Use for ad-hoc analysis not covered by other tools:
                - Dimensional breakdowns
                - Historical comparisons
                - Custom metric combinations
                
                Returns results as markdown table.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL query to execute"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_experiment_brief",
                "description": """Get experiment context including feature description.
                
                Returns:
                - brief_summary: Concise feature description
                - details: Additional context
                - Brief doc link, status, rollout %
                
                Use this to understand WHAT the feature does and WHY it exists.
                Essential for reflection when metrics show unexpected patterns.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Experiment project name"
                        },
                        "date": {
                            "type": "string",
                            "description": "Date (defaults to today)"
                        }
                    },
                    "required": ["project_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_metric_definition",
                "description": """Get complete metric definition from TALLEYRAND_METRICS.
                
                Returns:
                - Description: What the metric measures
                - Spec: How it's calculated (JSON)
                - Desired direction: Expected direction of improvement
                
                Use this to understand HOW a metric is calculated and WHAT it means.
                Essential for reflection to understand metric relationships.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric_name": {
                            "type": "string",
                            "description": "Metric name (e.g., 'checkout_conversion', 'mau')"
                        }
                    },
                    "required": ["metric_name"]
                }
            }
        }
    ]


# ========================================
# TOOL ROUTER
# ========================================

def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    Route tool calls to their implementations.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Dictionary of arguments for the tool
        
    Returns:
        Tool execution result as string
    """
    if tool_name == "get_live_experiments":
        return get_live_experiments(arguments.get('date'))
    
    elif tool_name == "get_significant_metrics":
        return get_significant_metrics(
            arguments['analysis_id'],
            arguments.get('metric_type')
        )
    
    elif tool_name == "get_all_metrics_for_analysis":
        return get_all_metrics_for_analysis(
            arguments['analysis_id'],
            arguments.get('dimension_cut', 'overall')
        )
    
    elif tool_name == "parse_metric_spec":
        return parse_metric_spec(arguments['spec_json'])
    
    elif tool_name == "find_source_sql":
        return find_source_sql(arguments['measure_id'])
    
    elif tool_name == "query_snowflake":
        return query_snowflake(arguments['query'])
    
    elif tool_name == "get_experiment_brief":
        return get_experiment_brief(
            arguments['project_name'],
            arguments.get('date')
        )
    
    elif tool_name == "get_metric_definition":
        return get_metric_definition(arguments['metric_name'])
    
    else:
        return f"Error: Unknown tool '{tool_name}'"

