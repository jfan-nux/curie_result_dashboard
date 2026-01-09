"""
Experiment Callout Agent

A ReAct agent for analyzing experiments and generating daily callouts.

Usage:
    from agent import ExperimentCalloutAgent, run_daily_callout
    
    # Generate callout for today
    callout = run_daily_callout()
    
    # Or use the agent directly
    agent = ExperimentCalloutAgent()
    callout = agent.generate_callout(date="2026-01-06")
"""

from agent.react_agent import ExperimentCalloutAgent, run_daily_callout

__all__ = [
    'ExperimentCalloutAgent',
    'run_daily_callout',
]

