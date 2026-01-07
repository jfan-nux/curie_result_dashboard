# PRD: Daily Experiment Callout Agent

## 1. Executive Summary

**Agent Name:** NUX Experiment Monitor  
**Purpose:** Automated daily monitoring and intelligent callouts for in-flight experiments  
**Output:** Daily digest highlighting significant metric movements with contextual analysis

## 2. Problem Statement

Currently, experiment owners must:
- Manually check Curie dashboards daily
- Identify significant metric movements across multiple dimensions
- Research metric definitions when anomalies occur
- Read experiment briefs to understand context
- Synthesize findings into actionable callouts

**This agent automates the entire workflow.**

---

## 3. User Stories

### Primary Users: Product Managers, Data Scientists, Experiment Owners

**As a PM, I want to:**
- Receive daily alerts when my experiments show significant movements
- Understand which metrics moved (primary, secondary, guardrail)
- Get context on why a metric might have moved
- See metric definitions without hunting through documentation
- Read a concise summary without checking multiple dashboards

**As a Data Scientist, I want to:**
- Identify experiments requiring immediate attention
- Understand metric composition (spec, sources, SQL)
- See dimensional breakdowns of significant movements
- Trace metrics back to source tables and SQL logic

---

## 4. Core Functionality

### 4.1 Data Sources

#### Input Tables:
1. **`proddb.fionafan.coda_experiments_focused`**
   - Filter: `view_name = 'Live Experiments'`
   - Key columns: `project_name`, `brief`, `details`, `curie_ios`, `curie_android`

2. **`proddb.fionafan.nux_curie_result_daily`**
   - Key columns: `metric_name`, `metric_type`, `dimension_cut_name`, `stat_sig`, `metric_impact_relative`, `p_value`, `metric_spec`, `metric_description`

3. **`CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_METRICS`**
   - For metric definitions: `name`, `description`, `spec`, `desired_direction`

4. **`CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_SOURCE`**
   - For source SQL: `id`, `name`, `compute_spec:snowflakeSpec:sql`

#### External Sources:
- Google Docs (experiment briefs)
- Images in Google Docs (screenshots, charts)

---

### 4.2 Analysis Workflow

```
┌─────────────────────────────────────────┐
│ Step 1: Identify Live Experiments      │
│ - Query Coda table for live experiments│
│ - Extract analysis IDs from Curie links│
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Step 2: Fetch Curie Results            │
│ - Join with nux_curie_result_daily     │
│ - Filter for today's data              │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Step 3: Flag Significant Metrics       │
│ Priority order:                         │
│ 1. Primary (topline) - sig pos/neg     │
│ 2. Secondary - sig pos/neg             │
│ 3. Guardrail - sig negative only       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Step 4: Deep Dive (if flags exist)     │
│ - Parse metric_spec JSON               │
│ - Extract measure IDs                  │
│ - Query source SQL definitions         │
│ - Understand metric composition        │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Step 5: Gather Context                 │
│ - Crawl Google Doc from 'brief' column│
│ - Extract experiment description       │
│ - Parse images (charts, mockups)      │
│ - Use 'details' if brief unavailable  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Step 6: Generate Callout               │
│ - Synthesize findings                  │
│ - Format for readability               │
│ - Minimal emoji use                    │
└─────────────────────────────────────────┘
```

---

### 4.3 Metric Analysis Priority

#### Level 1: Primary Metrics (Topline)
```sql
WHERE metric_type = 'primary'
  AND stat_sig IN ('significant positive', 'significant negative')
  AND dimension_cut_name = 'overall'
ORDER BY ABS(metric_impact_relative) DESC
```

**Analysis includes:**
- Overall impact (all dimensions starting with 'overall')
- Dimensional breakdowns showing where impact is concentrated
- Direction vs. desired direction check

#### Level 2: Secondary Metrics
```sql
WHERE metric_type = 'secondary'
  AND stat_sig IN ('significant positive', 'significant negative')
```

**Analysis includes:**
- Supporting evidence for primary movements
- Unexpected movements requiring investigation

#### Level 3: Guardrail Metrics
```sql
WHERE metric_type = 'guardrail'
  AND stat_sig = 'significant negative'
```

**Analysis includes:**
- Safety checks
- Potential experiment blockers

---

### 4.4 Metric Deep Dive Process

When flags are triggered, agent performs deep analysis:

#### 4.4.1 Parse Metric Spec
```json
{
  "type": "METRIC_TYPE_RATIO",
  "ratioParam": {
    "numeratorMeasure": {
      "id": "d3ab4060-2f73-4956-8d93-d20d3e72fec5",
      "name": "system_checkout_success_day"
    },
    "denominatorMeasure": {
      "id": "0431609e-2abc-4886-8cb6-701b748a255b",
      "name": "explore_page_visit_day"
    },
    "numeratorAggregation": "AGGREGATION_TYPE_COUNT_DISTINCT",
    "denominatorAggregation": "AGGREGATION_TYPE_NULL_IF_ZERO_COUNT_DISTINCT"
  }
}
```

**Extract:**
- Metric type (SIMPLE, RATIO, FUNNEL)
- Component measures (numerator/denominator)
- Aggregation methods

#### 4.4.2 Find Source SQL
```sql
SELECT 
  id,
  name, 
  description,
  compute_spec:lookBackPeriod as lookBackPeriod, 
  compute_spec:lookBackUnit as lookBackUnit, 
  compute_spec:snowflakeSpec:sql as sql,
  'https://ops.doordash.team/decision-systems/unified-metrics-platform/sources/'||id as url
FROM CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_SOURCE 
WHERE id IN (
  -- Extract measure source IDs from metric_spec
);
```

**Provides:**
- Raw SQL definitions
- Lookback periods
- Data freshness
- Links to ops.doordash.team

---

## 5. Agent Tools & Capabilities

### 5.1 Data Access Tools

#### Tool 1: `query_snowflake`
```python
def query_snowflake(query: str) -> pd.DataFrame:
    """Execute Snowflake query and return results."""
```

#### Tool 2: `get_live_experiments`
```python
def get_live_experiments() -> List[Dict]:
    """Fetch live experiments from Coda table."""
```

#### Tool 3: `get_curie_results`
```python
def get_curie_results(analysis_id: str, date: str) -> pd.DataFrame:
    """Fetch Curie results for specific analysis."""
```

#### Tool 4: `parse_metric_spec`
```python
def parse_metric_spec(spec_json: str) -> Dict:
    """Parse metric_spec JSON to extract measures, types, aggregations."""
```

#### Tool 5: `find_source_sql`
```python
def find_source_sql(measure_id: str) -> Dict:
    """Fetch source SQL definition from TALLEYRAND_SOURCE."""
```

---

### 5.2 Context Gathering Tools

#### Tool 6: `crawl_google_doc`
```python
def crawl_google_doc(doc_url: str) -> Dict:
    """
    Crawl Google Doc and extract:
    - Text content (markdown format)
    - Images (URLs and descriptions)
    - Document structure (headings, sections)
    """
```

#### Tool 7: `analyze_image`
```python
def analyze_image(image_url: str, context: str) -> str:
    """
    Use Portkey + Vision model to analyze images:
    - Screenshots of UI/UX changes
    - Charts and graphs
    - Mockups and designs
    """
```

---

### 5.3 LLM Integration (Portkey)

#### Configuration:
```python
from portkey_ai import Portkey

portkey = Portkey(
    api_key=os.getenv("PORTKEY_API_KEY"),
    virtual_key="<your-virtual-key>",  # Claude/GPT-4
    config={
        "retry": {"attempts": 3},
        "cache": {"mode": "simple"},
        "logging": True
    }
)
```

#### Use Cases:
1. **Metric interpretation**: Explain metric movements in plain English
2. **Context synthesis**: Summarize experiment briefs
3. **Image analysis**: Understand UI changes from screenshots
4. **Anomaly detection**: Identify unexpected patterns
5. **Callout generation**: Write daily summaries

---

## 6. Output Format

### 6.1 Daily Callout Structure

```
# Daily Experiment Callout - [DATE]

## Summary
[X] experiments monitored
[Y] require attention (significant movements detected)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## [EXPERIMENT NAME]

**Status:** [Topline Flag / Secondary Flag / Guardrail Flag]
**Analysis ID:** [link to Curie]
**Brief:** [link to Google Doc]

### What Changed
- **[Metric Name]** ([dimension_cut_name]): [+X.X%] (p=[0.XX])
  - Direction: [significant positive/negative]
  - Impact: [interpretation]
  
### Metric Definition
[Metric description from TALLEYRAND_METRICS]

**Composition:**
- Type: [SIMPLE/RATIO/FUNNEL]
- Numerator: [measure_name] (source: [source_name])
- Denominator: [measure_name] (source: [source_name])
- Lookback: [X days]

### Experiment Context
[Summary from brief Google Doc]

### Dimensional Breakdown
| Dimension | Cut | Impact | P-value | Significance |
|-----------|-----|--------|---------|--------------|
| overall   | -   | +5.2%  | 0.01    | sig positive |
| platform  | iOS | +8.1%  | 0.001   | sig positive |
| platform  | Android | +2.1% | 0.15 | directional |

### Recommendation
[Agent's analysis and suggested action]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Next experiment...]
```

---

### 6.2 Severity Levels

#### Critical (Immediate attention)
- Primary metric: significant negative (opposite of desired direction)
- Guardrail metric: significant negative

#### Monitor (Keep watching)
- Secondary metric: significant movement
- Primary metric: directional (0.05 < p < 0.25)

#### On Track
- Primary metric: significant positive (matches desired direction)
- No guardrail concerns

---

## 7. Technical Architecture

### 7.1 Agent Framework

```python
class ExperimentCalloutAgent:
    """
    Daily experiment monitoring and callout generation agent.
    """
    
    def __init__(self):
        self.snowflake = SnowflakeHook()
        self.portkey = Portkey(api_key=...)
        self.tools = [
            query_snowflake,
            crawl_google_doc,
            parse_metric_spec,
            find_source_sql,
            analyze_image
        ]
    
    def run_daily_analysis(self, date: str):
        """Main orchestration method."""
        # 1. Get live experiments
        experiments = self.get_live_experiments()
        
        # 2. For each experiment, check Curie results
        flagged_experiments = []
        for exp in experiments:
            flags = self.check_metrics(exp, date)
            if flags:
                flagged_experiments.append((exp, flags))
        
        # 3. Deep dive on flagged experiments
        callouts = []
        for exp, flags in flagged_experiments:
            callout = self.generate_callout(exp, flags)
            callouts.append(callout)
        
        # 4. Format and send
        report = self.format_report(callouts, date)
        self.send_report(report)
    
    def check_metrics(self, experiment, date):
        """Check for significant metric movements."""
        pass
    
    def generate_callout(self, experiment, flags):
        """Generate detailed callout using LLM."""
        pass
```

---

### 7.2 Tool Implementations

#### Snowflake Query Tool
```python
@tool
def query_snowflake(query: str) -> str:
    """
    Execute Snowflake query and return results as formatted string.
    
    Args:
        query: SQL query to execute
        
    Returns:
        Results in markdown table format
    """
    with SnowflakeHook() as hook:
        df = hook.query_snowflake(query, method='pandas')
        return df.to_markdown()
```

#### Google Doc Crawler Tool
```python
@tool
def crawl_google_doc(doc_url: str) -> Dict[str, Any]:
    """
    Crawl Google Doc and extract content.
    
    Args:
        doc_url: Google Doc URL from 'brief' column
        
    Returns:
        {
            'text': 'Markdown formatted content',
            'images': [{'url': '...', 'caption': '...'}],
            'headings': ['Section 1', 'Section 2']
        }
    """
    # Use MCP googledocs tool
    doc_id = extract_doc_id(doc_url)
    content = mcp_convert_google_doc_to_markdown(doc_url)
    return parse_doc_content(content)
```

#### Metric Spec Parser Tool
```python
@tool
def parse_metric_spec(spec_json: str) -> Dict[str, Any]:
    """
    Parse metric_spec JSON to understand metric composition.
    
    Args:
        spec_json: JSON string from metric_spec column
        
    Returns:
        {
            'type': 'METRIC_TYPE_RATIO',
            'numerator': {'id': '...', 'name': '...'},
            'denominator': {'id': '...', 'name': '...'},
            'aggregations': {'num': 'COUNT_DISTINCT', 'den': '...'}
        }
    """
    spec = json.loads(spec_json)
    # Extract relevant fields based on metric type
    return extract_metric_components(spec)
```

#### Source SQL Finder Tool
```python
@tool
def find_source_sql(measure_id: str) -> Dict[str, str]:
    """
    Find source SQL definition for a measure.
    
    Args:
        measure_id: UUID from metric_spec
        
    Returns:
        {
            'source_name': 'consumer_volume_curie',
            'sql': 'SELECT ...',
            'lookback_period': 30,
            'lookback_unit': 'days',
            'url': 'https://ops.doordash.team/...'
        }
    """
    query = f"""
    SELECT 
        name,
        compute_spec:snowflakeSpec:sql as sql,
        compute_spec:lookBackPeriod as lookback_period,
        compute_spec:lookBackUnit as lookback_unit
    FROM CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_SOURCE
    WHERE id = '{measure_id}'
    """
    # Execute and return
```

---

### 7.3 Portkey Integration

#### Basic LLM Call
```python
def analyze_with_llm(context: str, prompt: str) -> str:
    """Use Portkey to call LLM."""
    response = portkey.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an experiment analysis expert."},
            {"role": "user", "content": f"{context}\n\n{prompt}"}
        ],
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000
    )
    return response.choices[0].message.content
```

#### Vision Analysis
```python
def analyze_experiment_screenshot(image_url: str, context: str) -> str:
    """Analyze UI screenshots from experiment briefs."""
    response = portkey.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Context: {context}\n\nWhat changes are shown in this screenshot?"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        model="gpt-4-vision-preview"
    )
    return response.choices[0].message.content
```

---

## 8. Emoji Usage Guidelines

### Restrained Usage Policy

**Allowed (sparingly):**
- Critical issues (max 1 per report)
- Warnings (max 2 per report)
- Successes (max 1 per report)
- Data references (max 3 per report)

**Not Allowed:**
- Decorative emoji (celebration, rocket, sparkles, etc.)
- Multiple emoji in sequence
- Emoji in metric names or technical descriptions

**Example - Good:**
```
Critical: guardrail checkout_error_rate increased 15% (p=0.01)
```

**Example - Bad:**
```
Uh oh! checkout_error_rate went up!
```

---

## 9. Sample Prompts for Agent

### System Prompt
```
You are an experiment analysis assistant for DoorDash's NUX team. 
Your role is to monitor live experiments and generate daily callouts.

Guidelines:
1. Be precise and technical when discussing metrics
2. Use minimal emoji (only for severity indicators)
3. Prioritize primary metrics, then secondary, then guardrails
4. Provide context from experiment briefs
5. Explain metric definitions when movements are significant
6. Suggest actionable next steps

When analyzing metrics:
- Check desired_direction against actual impact
- Consider dimensional breakdowns
- Look for correlated movements in related metrics
- Reference experiment goals from briefs
```

### Example Analysis Prompt
```
Analyze this experiment's Curie results:

Experiment: {project_name}
Brief: {brief_summary}

Significant Metrics:
{metrics_table}

Metric Definitions:
{metric_specs}

Tasks:
1. Interpret the metric movements in context of experiment goals
2. Identify if movements align with expected outcomes
3. Check for concerning patterns (guardrails, unexpected negatives)
4. Suggest whether to continue, ramp, or pause
5. Format as a callout following the template
```

---

## 10. Success Metrics

### Agent Performance
- **Coverage:** 100% of live experiments monitored daily
- **Accuracy:** >95% correct significance flagging
- **Latency:** Report generated within 10 minutes
- **False positives:** <5% (flag when no action needed)

### User Impact
- **Time saved:** 2-3 hours/day per PM (currently manual)
- **Response time:** Alerts within 1 hour of data availability
- **Adoption:** 80%+ of PMs use daily callouts
- **Satisfaction:** 4.5+ stars from users

---

## 11. Future Enhancements

### Phase 2
- Slack integration (post callouts to #nux-experiments)
- Email digests with customizable thresholds
- Historical trend comparison (week-over-week)
- Automatic hypothesis generation

### Phase 3
- Predictive alerts (before statistical significance)
- A/A test monitoring (detect setup issues)
- Cross-experiment correlation analysis
- Natural language queries ("Show me all experiments hurting MAU")

---

## 12. Open Questions

1. **Delivery method:** Slack, email, or web dashboard?
2. **Frequency:** Daily only, or real-time alerts for critical issues?
3. **Customization:** Per-user thresholds or team-wide defaults?
4. **Metric definitions:** Cache or query fresh each time?
5. **Image analysis:** Always analyze screenshots or only on request?

---

## 13. Implementation Roadmap

### Week 1-2: Foundation
- Set up data pipeline connections (Snowflake, Coda)
- Implement basic query tools
- Build metric spec parser

### Week 3-4: Core Logic
- Develop significance detection algorithm
- Implement metric deep-dive logic
- Build Google Doc crawler

### Week 5-6: LLM Integration
- Set up Portkey integration
- Develop callout generation prompts
- Implement vision analysis for screenshots

### Week 7-8: Testing & Refinement
- Test with historical data
- Refine prompts based on output quality
- User acceptance testing with PMs

### Week 9: Launch
- Deploy to production
- Monitor daily outputs
- Gather feedback

---

**Document Version:** 1.0  
**Last Updated:** January 6, 2026  
**Author:** Fiona Fan  
**Status:** Draft

