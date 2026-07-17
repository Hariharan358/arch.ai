"""
tax_agent.py — Autonomous Tax Filing Agent

Demonstrates:
  ✅ Claude Agent SDK (Anthropic tool_use loop)
  ✅ archaitools integration (pip install archaitools)
  ✅ Privacy-first PII sanitization
  ✅ Human Flourishing — makes taxes accessible

This agent autonomously:
  1. Estimates if the marketplace has a relevant tax workflow
  2. Purchases the best solution
  3. Presents a step-by-step execution plan
  4. Rates the workflow for community benefit

Prize targets:
  - Anthropic: Human Flourishing Track
  - Anthropic: Best Use of Claude Agent SDK
"""

from agent_runner import MarkAgent


TAX_SYSTEM_PROMPT = """You are a tax filing assistant powered by the Mark AI marketplace.

Your job is to help users file their taxes by finding pre-solved tax workflows.

Process:
1. Analyze the user's tax situation
2. Use mark_estimate to find matching workflows (this sanitizes PII automatically)
3. Review the solutions — check price, confidence, and coverage
4. Use mark_buy to purchase the best solution
5. Present the step-by-step filing instructions to the user
6. Use mark_rate to give feedback

Key principles:
- NEVER send PII to the marketplace (archaitools sanitizes automatically)
- Explain savings: marketplace workflow vs. solving from scratch
- Be specific about which tax forms are needed
- Highlight edge cases and gotchas from the workflow

Remember: you're making tax filing accessible to everyone. This is human flourishing."""


def run_tax_agent():
    """Run the tax filing demo."""
    agent = MarkAgent(
        name="tax-agent",
        system_prompt=TAX_SYSTEM_PROMPT,
        verbose=True,
    )

    # Realistic user query with PII (will be auto-sanitized by archaitools)
    task = (
        "I need to file my Ohio state taxes for 2024. "
        "I have a W2 from my employer, and I want to use itemized deductions. "
        "My income is around $85,000 and I live in Columbus. "
        "Can you find me the best workflow for this?"
    )

    trace = agent.run(task)

    print("\n📊 Agent Trace Summary")
    print(f"  Steps: {len(trace.steps)}")
    print(f"  Tools called: {trace.tools_called}")
    print(f"  Total latency: {trace.total_latency_ms:.0f}ms")
    print(f"  Success: {'✅' if trace.success else '❌'}")

    return trace


if __name__ == "__main__":
    run_tax_agent()
