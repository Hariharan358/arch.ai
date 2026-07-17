"""
with_archaitools.py — Simulates what an agent does WITH archaitools.

This is the "enhanced" agent: Claude with access to the Mark AI marketplace
via `pip install archaitools`. It uses mark_estimate → mark_buy → mark_rate
to get pre-solved expert workflows with edge cases and domain knowledge.

This file is used by the demo to show the AFTER state.
"""

import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ToolCall:
    tool_name: str
    tool_input: Dict[str, Any]
    result: Dict[str, Any]
    latency_ms: float


@dataclass
class EnhancedStep:
    step_number: int
    action: str
    reasoning: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    output: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0


@dataclass
class EnhancedTrace:
    task: str
    steps: List[EnhancedStep] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    accuracy_score: float = 0.0
    edge_cases_caught: List[str] = field(default_factory=list)
    tokens_saved_vs_baseline: int = 0
    savings_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "steps": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "reasoning": s.reasoning,
                    "tool_calls": [
                        {
                            "tool": tc.tool_name,
                            "input": tc.tool_input,
                            "result": tc.result,
                            "latency_ms": tc.latency_ms,
                        }
                        for tc in s.tool_calls
                    ],
                    "output": s.output,
                    "tokens_used": s.tokens_used,
                    "latency_ms": s.latency_ms,
                }
                for s in self.steps
            ],
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "accuracy_score": self.accuracy_score,
            "edge_cases_caught": self.edge_cases_caught,
            "tokens_saved_vs_baseline": self.tokens_saved_vs_baseline,
            "savings_percentage": self.savings_percentage,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Simulated archaitools-enhanced agent solving Ohio taxes
# ──────────────────────────────────────────────────────────────────────────────

def run_archaitools_agent(task: str, baseline_tokens: int = 4390) -> EnhancedTrace:
    """
    Simulate a Claude agent with archaitools solving Ohio tax filing.

    The agent calls mark_estimate (free), evaluates the results,
    calls mark_buy to purchase the best workflow, then delivers
    a complete plan with ALL edge cases covered.
    """
    trace = EnhancedTrace(task=task)
    start = time.time()

    # ── Step 1: Agent thinks and calls mark_estimate ──────────────────────
    step1 = EnhancedStep(
        step_number=1,
        action="mark_estimate",
        reasoning=(
            "The user needs to file Ohio 2024 taxes. Instead of reasoning from scratch, "
            "let me search the Mark AI marketplace for a pre-solved workflow. "
            "I'll call mark_estimate — it's free, and it will automatically sanitize "
            "any PII from the query before searching."
        ),
        tokens_used=180,
        latency_ms=1400,
    )
    step1.tool_calls.append(ToolCall(
        tool_name="mark_estimate",
        tool_input={
            "query": "File Ohio 2024 state taxes with W2 income and itemized deductions",
            "context": {
                "state": "ohio",
                "year": 2024,
                "income_bracket": "80k-100k",
                "filing_type": "W2",
                "deduction_type": "itemized",
            },
        },
        result={
            "session_id": "sess_demo_tax_001",
            "num_solutions": 3,
            "best_match": {
                "solution_id": "sol_1",
                "title": "Ohio IT-1040 (W2, Itemized) — Complete Filing Workflow",
                "confidence": 0.94,
                "pricing": {
                    "total_cost_tokens": 500,
                    "estimated_savings_percentage": 73,
                    "breakdown": {
                        "base_cost": 200,
                        "execution_tokens": 300,
                        "rating_discount": 0,
                    },
                },
                "coverage": ["IT-1040", "Schedule A", "SD-100", "city tax", "RITA"],
                "rating": 4.8,
                "usage_count": 47,
            },
            "alternatives": [
                {"solution_id": "sol_2", "title": "Generic State Tax Filing", "confidence": 0.71},
                {"solution_id": "sol_3", "title": "Ohio Simple (Standard Deduction)", "confidence": 0.58},
            ],
            "privacy": {
                "pii_detected": ["income_bracket"],
                "action": "bucketed to 80k-100k (exact income never sent to marketplace)",
            },
        },
        latency_ms=1200,
    ))
    step1.output = (
        "Found 3 matching workflows. Best match: 'Ohio IT-1040 (W2, Itemized)' — "
        "94% confidence, 500 tokens, covers IT-1040 + Schedule A + SD-100 + city tax + RITA. "
        "This saves ~73% vs solving from scratch. Rating: 4.8★ from 47 users."
    )
    trace.steps.append(step1)

    # ── Step 2: Agent evaluates and calls mark_buy ────────────────────────
    step2 = EnhancedStep(
        step_number=2,
        action="mark_buy",
        reasoning=(
            "The marketplace found a 94% confidence match that covers ALL Ohio filing "
            "requirements including SD-100 and city tax — things I might miss solving "
            "from scratch. At 500 tokens with 73% savings, this is an excellent deal. "
            "It has a 4.8★ rating from 47 users. Purchasing now."
        ),
        tokens_used=150,
        latency_ms=900,
    )
    step2.tool_calls.append(ToolCall(
        tool_name="mark_buy",
        tool_input={
            "session_id": "sess_demo_tax_001",
            "solution_id": "sol_1",
        },
        result={
            "purchase_id": "purch_demo_001",
            "tokens_charged": 500,
            "execution_plan": {
                "title": "Ohio IT-1040 (W2, Itemized) — Complete Filing Workflow",
                "total_steps": 10,
                "workflows": [
                    {
                        "workflow_id": "ohio_w2_itemized_2024",
                        "title": "Ohio 2024 IT-1040 Filing",
                        "steps": [
                            {"step": 1, "action": "Gather W2 forms from all employers"},
                            {"step": 2, "action": "Calculate Ohio AGI (federal AGI − state pension − 529 contributions)"},
                            {"step": 3, "action": "Complete Schedule A — itemized deductions (FULL property tax — no SALT cap on Ohio return)"},
                            {"step": 4, "action": "Compare: itemized ($X) vs standard deduction ($9,050 for MFJ 2024)"},
                            {"step": 5, "action": "Apply 2024 Ohio graduated brackets: $0-$26,050 at 0%, $26,051-$100k at 2.765%"},
                            {"step": 6, "action": "Apply Joint Filing Credit ($650 automatic for MFJ)"},
                            {"step": 7, "action": "Complete SD-100 for school district income tax"},
                            {"step": 8, "action": "File city return via RITA/CCA (Columbus: 2.5% rate)"},
                            {"step": 9, "action": "Apply W2 box 17 withholding credits"},
                            {"step": 10, "action": "File electronically via Ohio eFile"},
                        ],
                        "edge_cases": [
                            "Ohio does NOT have a $10,000 SALT cap — full property tax deduction allowed",
                            "Columbus residents must also file city RITA return separately",
                            "SD-100 required if school district has income tax (most do)",
                            "Joint Filing Credit is AUTOMATIC for MFJ — $650 credit, many filers miss this",
                            "If worked in different city than residence, may owe tax to both — check credit",
                            "First $26,050 of income is TAX-FREE under 2024 Ohio brackets (0% rate)",
                        ],
                        "domain_knowledge": {
                            "ohio_2024_brackets": {
                                "0-26050": "0%",
                                "26051-100000": "2.765%",
                                "100001-115300": "3.226%",
                                "115301+": "3.688%",
                            },
                            "standard_deduction_mfj_2024": 9050,
                            "joint_filing_credit": 650,
                            "columbus_city_rate": "2.5%",
                        },
                    }
                ],
            },
        },
        latency_ms=800,
    ))
    step2.output = (
        "Purchased workflow for 500 tokens. Received complete 10-step execution plan "
        "with 6 edge cases and domain knowledge including correct 2024 brackets."
    )
    trace.steps.append(step2)

    # ── Step 3: Agent presents the plan to the user ───────────────────────
    step3 = EnhancedStep(
        step_number=3,
        action="present_plan",
        reasoning=(
            "Now I have a complete, expert-verified execution plan. Let me present "
            "this to the user with all the important Ohio-specific details highlighted."
        ),
        tokens_used=420,
        latency_ms=1100,
    )
    step3.output = (
        "Here's your complete Ohio 2024 tax filing plan:\n\n"
        "📋 FORMS REQUIRED:\n"
        "  • IT-1040 (main Ohio return)\n"
        "  • Schedule A (itemized deductions)\n"
        "  • SD-100 (school district tax)\n"
        "  • City return via RITA/CCA\n\n"
        "💡 CRITICAL OHIO-SPECIFIC DETAILS:\n"
        "  1. NO SALT cap on Ohio return — deduct FULL property tax\n"
        "  2. First $26,050 of income is TAX-FREE (0% bracket)\n"
        "  3. $650 Joint Filing Credit is AUTOMATIC for married filing jointly\n"
        "  4. Columbus city tax is 2.5% — filed separately via RITA\n"
        "  5. SD-100 is REQUIRED if your school district levies income tax\n\n"
        "📊 ESTIMATED TAX CALCULATION:\n"
        "  Ohio AGI: ~$85,000\n"
        "  Taxable (after $26,050 exempt): ~$58,950\n"
        "  Ohio tax (2.765% on $58,950): ~$1,630\n"
        "  Joint Filing Credit: −$650\n"
        "  Net Ohio tax: ~$980\n"
        "  + School district tax: varies\n"
        "  + Columbus city tax: ~$2,125\n\n"
        "This plan has been used by 47 other filers with a 4.8★ rating."
    )
    trace.steps.append(step3)

    # ── Step 4: Agent rates the workflow ───────────────────────────────────
    step4 = EnhancedStep(
        step_number=4,
        action="mark_rate",
        reasoning=(
            "The workflow provided accurate, complete information. Let me rate it "
            "to help improve marketplace quality for future users."
        ),
        tokens_used=80,
        latency_ms=400,
    )
    step4.tool_calls.append(ToolCall(
        tool_name="mark_rate",
        tool_input={
            "workflow_id": "ohio_w2_itemized_2024",
            "rating": 5,
        },
        result={
            "success": True,
            "workflow_id": "ohio_w2_itemized_2024",
            "new_average_rating": 4.82,
            "total_ratings": 48,
        },
        latency_ms=200,
    ))
    step4.output = "Rated workflow 5★. New average: 4.82★ (48 ratings)."
    trace.steps.append(step4)

    # ── Totals ────────────────────────────────────────────────────────────
    trace.total_tokens = sum(s.tokens_used for s in trace.steps) + 500  # include marketplace cost
    trace.total_latency_ms = sum(s.latency_ms for s in trace.steps)
    trace.accuracy_score = 100.0  # all edge cases caught
    trace.tokens_saved_vs_baseline = baseline_tokens - trace.total_tokens
    trace.savings_percentage = round(
        (trace.tokens_saved_vs_baseline / baseline_tokens) * 100, 1
    )

    trace.edge_cases_caught = [
        "✅ Ohio has NO SALT cap — full property tax deduction (baseline missed this)",
        "✅ SD-100 school district tax form required (baseline missed this)",
        "✅ $650 Joint Filing Credit is automatic for MFJ (baseline missed this)",
        "✅ Local city tax is MANDATORY, not optional (baseline dismissed this)",
        "✅ Correct 2024 brackets with $26,050 at 0% (baseline used outdated brackets)",
        "✅ RITA/CCA filing requirement for city return (baseline ignored this)",
    ]

    return trace
