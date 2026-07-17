"""
shopping_agent.py — Autonomous Shopping & Commerce Agent

Demonstrates:
  ✅ Claude Agent SDK (Anthropic tool_use loop)
  ✅ archaitools integration (pip install archaitools)
  ✅ Multi-turn commerce reasoning
  ✅ Budget-aware purchasing

Prize targets:
  - Visa: Future of Commerce
  - Anthropic: Best Use of Claude Agent SDK
"""

from agent_runner import MarkAgent


SHOPPING_SYSTEM_PROMPT = """You are a smart shopping assistant powered by the Mark AI marketplace.

Your job is to help users find the best products and deals by leveraging
pre-solved comparison and shopping workflows from the marketplace.

Process:
1. Understand what the user wants to buy and their budget
2. Use mark_estimate to find relevant shopping/comparison workflows
3. Purchase the best workflow that covers their product category
4. Present structured comparison with pros/cons
5. Rate the workflow based on how useful it was

Key principles:
- Optimize for VALUE, not just lowest price
- Always show multiple options with tradeoffs
- Consider reviews, warranty, shipping in recommendations
- Be transparent about marketplace costs vs. savings"""


def run_shopping_agent():
    """Run the shopping agent demo."""
    agent = MarkAgent(
        name="shopping-agent",
        system_prompt=SHOPPING_SYSTEM_PROMPT,
        verbose=True,
    )

    task = (
        "I want to buy a new laptop for software development. "
        "Budget is $1500-2000. I need at least 32GB RAM, good keyboard, "
        "and a screen suitable for long coding sessions. "
        "Find me the best workflow to compare options."
    )

    trace = agent.run(task)
    return trace


if __name__ == "__main__":
    run_shopping_agent()
