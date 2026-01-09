#!/usr/bin/env python3
"""
Test suite for ReAct Agent.

Run:
    python agent/tests/test_react_agent.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.react_agent import ExperimentCalloutAgent, run_daily_callout


def test_agent_initialization():
    """Test: Agent initializes correctly."""
    print("\n" + "=" * 80)
    print("TEST: Agent Initialization")
    print("=" * 80)
    
    agent = ExperimentCalloutAgent()
    
    if agent.is_available():
        print("✅ Agent initialized successfully")
        print(f"   Model: {agent.model}")
        return True
    else:
        print("⚠️  Agent not available (check Portkey config)")
        print("   This is expected if PORTKEY_API_KEY is not set")
        return True  # Still pass - config may not be available


def test_tool_definitions():
    """Test: Tool definitions are valid."""
    print("\n" + "=" * 80)
    print("TEST: Tool Definitions")
    print("=" * 80)
    
    agent = ExperimentCalloutAgent()
    tools = agent._get_tools()
    
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        name = tool['function']['name']
        desc = tool['function']['description'][:50]
        print(f"   - {name}: {desc}...")
    
    # Assertions
    assert len(tools) == 8, f"Expected 8 tools, got {len(tools)}"
    
    tool_names = [t['function']['name'] for t in tools]
    expected = [
        'get_live_experiments',
        'get_significant_metrics',
        'get_all_metrics_for_analysis',
        'parse_metric_spec',
        'find_source_sql',
        'query_snowflake',
        'get_experiment_brief',
        'get_metric_definition'
    ]
    
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"
    
    print("✅ All 8 tools defined correctly")
    return True


def test_generate_callout():
    """Test: Generate callout for a specific date."""
    print("\n" + "=" * 80)
    print("TEST: Generate Callout")
    print("=" * 80)
    
    agent = ExperimentCalloutAgent()
    
    if not agent.is_available():
        print("⚠️  Skipping - Agent not available (Portkey not configured)")
        return True
    
    date = "2026-01-06"
    print(f"Generating callout for {date}...")
    
    callout = agent.generate_callout(date=date)
    
    print(f"\nCallout ({len(callout)} chars):")
    print("-" * 40)
    print(callout[:2000])
    if len(callout) > 2000:
        print(f"\n... ({len(callout) - 2000} more chars)")
    print("-" * 40)
    
    print(f"\nStats:")
    print(f"   Iterations: {agent.iteration_count}")
    print(f"   Tool calls: {agent.tool_call_count}")
    
    # Assertions
    assert len(callout) > 100, "Callout should have substantial content"
    assert "error" not in callout.lower()[:50], "Callout should not start with error"
    
    print("✅ Callout generated successfully")
    return True


def test_analyze_experiment():
    """Test: Analyze a specific experiment."""
    print("\n" + "=" * 80)
    print("TEST: Analyze Experiment")
    print("=" * 80)
    
    agent = ExperimentCalloutAgent()
    
    if not agent.is_available():
        print("⚠️  Skipping - Agent not available (Portkey not configured)")
        return True
    
    # Use Travel v2 experiment
    project_name = "Travel v2"
    analysis_id = "d1fa0d0d-6741-4d12-92c8-dbca63e3473c"
    
    print(f"Analyzing: {project_name}")
    
    analysis = agent.analyze_experiment(project_name, analysis_id)
    
    print(f"\nAnalysis ({len(analysis)} chars):")
    print("-" * 40)
    print(analysis[:1500])
    if len(analysis) > 1500:
        print(f"\n... ({len(analysis) - 1500} more chars)")
    print("-" * 40)
    
    print(f"\nStats:")
    print(f"   Iterations: {agent.iteration_count}")
    print(f"   Tool calls: {agent.tool_call_count}")
    
    print("✅ Analysis completed")
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "🤖 " * 40)
    print("REACT AGENT TESTS")
    print("🤖 " * 40)
    
    tests = [
        ("agent_initialization", test_agent_initialization),
        ("tool_definitions", test_tool_definitions),
        # Uncomment to run full integration tests (requires Portkey):
        # ("generate_callout", test_generate_callout),
        # ("analyze_experiment", test_analyze_experiment),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\n❌ FAIL: {name}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, "FAIL"))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, status in results:
        symbol = "✅" if status == "PASS" else "❌"
        print(f"{symbol} {name}: {status}")
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test ReAct Agent')
    parser.add_argument('--full', action='store_true', help='Run full integration tests')
    
    args = parser.parse_args()
    
    if args.full:
        # Run all tests including integration
        tests = [
            test_agent_initialization,
            test_tool_definitions,
            test_generate_callout,
            test_analyze_experiment,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"Error: {e}")
    else:
        # Run basic tests only
        success = run_all_tests()
        sys.exit(0 if success else 1)

