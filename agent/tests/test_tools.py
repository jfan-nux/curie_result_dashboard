#!/usr/bin/env python3
"""
Test suite for agent tools.

Run all tests:
    python -m pytest agent/tests/test_tools.py -v

Run specific test:
    python agent/tests/test_tools.py --test get_live_experiments
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.tools import (
    get_live_experiments,
    get_significant_metrics,
    get_all_metrics_for_analysis,
    parse_metric_spec,
    find_source_sql,
    get_experiment_brief,
    get_metric_definition,
    query_snowflake
)


def test_get_live_experiments():
    """Test: Get live experiments from Coda table."""
    print("\n" + "=" * 80)
    print("TEST: get_live_experiments")
    print("=" * 80)
    
    date = "2026-01-06"
    result = get_live_experiments(date=date)
    
    print(f"\nResult:\n{result}\n")
    
    # Assertions
    assert "project_name" in result.lower(), "Should include project_name column"
    assert "analysis_id" in result.lower(), "Should include analysis_id column"
    assert len(result) > 100, "Should return substantial data"
    
    print("✅ PASS: get_live_experiments")
    return True


def test_get_significant_metrics():
    """Test: Get significant metrics for an experiment with metric_type classification."""
    print("\n" + "=" * 80)
    print("TEST: get_significant_metrics")
    print("=" * 80)
    
    # Use Travel v2 analysis ID
    analysis_id = "d1fa0d0d-6741-4d12-92c8-dbca63e3473c"
    
    print(f"\n--- Testing all significant metrics ---")
    result_all = get_significant_metrics(analysis_id)
    print(f"\nResult (first 1500 chars):\n{result_all[:1500]}...\n")
    
    print(f"\n--- Testing primary metrics only ---")
    result_primary = get_significant_metrics(analysis_id, metric_type="primary")
    print(f"\nResult:\n{result_primary}\n")
    
    print(f"\n--- Testing guardrail metrics (sig negative only) ---")
    result_guardrail = get_significant_metrics(analysis_id, metric_type="guardrail")
    print(f"\nResult:\n{result_guardrail}\n")
    
    # Assertions
    if "no significant metrics" not in result_all.lower():
        assert "metric_name" in result_all.lower(), "Should include metric columns"
        assert "stat_sig" in result_all.lower(), "Should include stat_sig column"
        assert "metric_type" in result_all.lower(), "Should include metric_type column"
    
    print("✅ PASS: get_significant_metrics")
    return True


def test_get_all_metrics_for_analysis():
    """Test: Get all metrics (including non-significant) for an analysis, sorted by impact magnitude."""
    print("\n" + "=" * 80)
    print("TEST: get_all_metrics_for_analysis")
    print("=" * 80)
    
    analysis_id = "d1fa0d0d-6741-4d12-92c8-dbca63e3473c"
    
    result = get_all_metrics_for_analysis(analysis_id, dimension_cut="overall")
    
    print(f"\nResult (first 2000 chars):\n{result[:2000]}...\n")
    
    # Assertions
    if "no metrics found" not in result.lower():
        assert "metric_name" in result.lower(), "Should include metrics"
        assert "metric_impact_relative" in result.lower(), "Should include metric impact"
        assert "metric_desired_direction" in result.lower(), "Should include desired direction"
    
    print("✅ PASS: get_all_metrics_for_analysis")
    return True


def test_parse_metric_spec():
    """Test: Parse metric spec JSON."""
    print("\n" + "=" * 80)
    print("TEST: parse_metric_spec")
    print("=" * 80)
    
    # Test SIMPLE metric
    simple_spec = '''
    {
      "simpleParam": {
        "aggregation": "AGGREGATION_TYPE_SUM",
        "measure": {
          "id": "d4d04291-ba2f-4508-85ca-b8a11bee8c81",
          "name": "cross_platform_orders",
          "sourceId": "455ec10a-240c-4428-9540-b1e741811ace"
        }
      },
      "type": "METRIC_TYPE_SIMPLE"
    }
    '''
    
    print("\n--- Testing SIMPLE metric ---")
    result_simple = parse_metric_spec(simple_spec)
    print(f"\nResult:\n{result_simple}\n")
    
    # Test RATIO metric
    ratio_spec = '''
    {
      "ratioParam": {
        "denominatorAggregation": "AGGREGATION_TYPE_NULL_IF_ZERO_COUNT_DISTINCT",
        "denominatorMeasure": {
          "id": "0431609e-2abc-4886-8cb6-701b748a255b",
          "name": "explore_page_visit_day"
        },
        "denominatorType": "DENOMINATOR_TYPE_MEASURE",
        "numeratorAggregation": "AGGREGATION_TYPE_COUNT_DISTINCT",
        "numeratorMeasure": {
          "id": "d3ab4060-2f73-4956-8d93-d20d3e72fec5",
          "name": "system_checkout_success_day"
        }
      },
      "type": "METRIC_TYPE_RATIO"
    }
    '''
    
    print("\n--- Testing RATIO metric ---")
    result_ratio = parse_metric_spec(ratio_spec)
    print(f"\nResult:\n{result_ratio}\n")
    
    # Assertions
    assert "metric_type" in result_simple.lower(), "Should parse metric type"
    assert "measures" in result_simple.lower(), "Should extract measures"
    assert "numerator" in result_ratio.lower(), "RATIO should have numerator"
    assert "denominator" in result_ratio.lower(), "RATIO should have denominator"
    
    print("✅ PASS: parse_metric_spec")
    return True


def test_find_source_sql():
    """Test: Find source SQL for a source."""
    print("\n" + "=" * 80)
    print("TEST: find_source_sql")
    print("=" * 80)
    
    # Use a known source ID (from parse_metric_spec output)
    source_id = "455ec10a-240c-4428-9540-b1e741811ace"  # webx_visitor_conversion_events
    
    result = find_source_sql(source_id)
    
    print(f"\nResult:\n{result[:500]}...\n")  # Truncate for readability
    
    # Assertions - this source should be found
    assert "no source found" not in result.lower(), "Source should be found"
    assert "source name" in result.lower(), "Should include source name"
    assert "sql" in result.lower(), "Should include SQL definition"
    assert "lookback" in result.lower(), "Should include lookback period"
    
    print("✅ PASS: find_source_sql")
    return True




def test_get_experiment_brief():
    """Test: Get experiment brief and context."""
    print("\n" + "=" * 80)
    print("TEST: get_experiment_brief")
    print("=" * 80)
    
    project_name = "Travel v2"
    
    result = get_experiment_brief(project_name, date="2026-01-06")
    
    print(f"\nResult:\n{result}\n")
    
    # Assertions
    if "not found" not in result.lower():
        assert "experiment:" in result.lower(), "Should include experiment name"
        assert "feature description" in result.lower(), "Should include description"
    
    print("✅ PASS: get_experiment_brief")
    return True


def test_get_metric_definition():
    """Test: Get metric definition from TALLEYRAND_METRICS."""
    print("\n" + "=" * 80)
    print("TEST: get_metric_definition")
    print("=" * 80)
    
    # Test with a common metric
    metric_name = "checkout_conversion"
    
    result = get_metric_definition(metric_name)
    
    print(f"\nResult:\n{result}\n")
    
    # Assertions
    if "not found" not in result.lower():
        assert "metric:" in result.lower(), "Should include metric name"
        assert "description" in result.lower(), "Should include description"
        assert "specification" in result.lower(), "Should include spec"
    
    print("✅ PASS: get_metric_definition")
    return True


def test_query_snowflake():
    """Test: Execute custom Snowflake query."""
    print("\n" + "=" * 80)
    print("TEST: query_snowflake")
    print("=" * 80)
    
    query = """
    SELECT COUNT(*) as experiment_count
    FROM proddb.fionafan.coda_experiments_focused
    WHERE view_name = 'Live Experiments'
      AND DATE(fetched_at) = '2026-01-06'
    """
    
    result = query_snowflake(query)
    
    print(f"\nResult:\n{result}\n")
    
    # Assertions
    assert "experiment_count" in result.lower(), "Should return query results"
    
    print("✅ PASS: query_snowflake")
    return True


# ========================================
# TEST RUNNER
# ========================================

def run_all_tests():
    """Run all tool tests."""
    
    print("\n" + "🧪 " * 40)
    print("RUNNING ALL TOOL TESTS")
    print("🧪 " * 40)
    
    tests = [
        ("get_live_experiments", test_get_live_experiments),
        ("get_significant_metrics", test_get_significant_metrics),
        ("get_all_metrics_for_analysis", test_get_all_metrics_for_analysis),
        ("parse_metric_spec", test_parse_metric_spec),
        ("find_source_sql", test_find_source_sql),
        ("get_experiment_brief", test_get_experiment_brief),
        ("get_metric_definition", test_get_metric_definition),
        ("query_snowflake", test_query_snowflake),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\n❌ FAIL: {test_name}")
            print(f"Error: {e}")
            results.append((test_name, "FAIL"))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, status in results:
        symbol = "✅" if status == "PASS" else "❌"
        print(f"{symbol} {test_name}: {status}")
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    return passed == total


def run_single_test(test_name: str):
    """Run a single test by name."""
    
    test_map = {
        "get_live_experiments": test_get_live_experiments,
        "get_significant_metrics": test_get_significant_metrics,
        "get_all_metrics_for_analysis": test_get_all_metrics_for_analysis,
        "parse_metric_spec": test_parse_metric_spec,
        "find_source_sql": test_find_source_sql,
        "get_experiment_brief": test_get_experiment_brief,
        "get_metric_definition": test_get_metric_definition,
        "query_snowflake": test_query_snowflake,
    }
    
    if test_name not in test_map:
        print(f"❌ Unknown test: {test_name}")
        print(f"Available tests: {', '.join(test_map.keys())}")
        return False
    
    try:
        return test_map[test_name]()
    except Exception as e:
        print(f"\n❌ FAIL: {test_name}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test agent tools')
    parser.add_argument(
        '--test',
        type=str,
        default=None,
        help='Run specific test (e.g., get_live_experiments)'
    )
    
    args = parser.parse_args()
    
    if args.test:
        # Run single test
        success = run_single_test(args.test)
        sys.exit(0 if success else 1)
    else:
        # Run all tests
        success = run_all_tests()
        sys.exit(0 if success else 1)

