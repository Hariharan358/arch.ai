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
    Simulate a Claude agent with archaitools solving Tamil Nadu tax filing.

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
            "The user needs to file Tamil Nadu (Chennai) tax returns for FY 2024-25. "
            "Instead of reasoning from scratch, let me search the Mark AI marketplace "
            "for a pre-solved tax filing workflow. I'll call mark_estimate — it's "
            "free and automatically handles any potential PII."
        ),
        tokens_used=180,
        latency_ms=1400,
    )
    step1.tool_calls.append(ToolCall(
        tool_name="mark_estimate",
        tool_input={
            "query": "File Tamil Nadu FY 2024-25 taxes with Form 16, Old Regime, and Chennai Professional Tax",
            "context": {
                "state": "tamilnadu",
                "city": "chennai",
                "year": "2024-25",
                "income_bracket": "8L-10L",
                "filing_type": "Form 16",
                "deduction_type": "old_regime",
            },
        },
        result={
            "session_id": "sess_demo_tax_001",
            "num_solutions": 3,
            "best_match": {
                "solution_id": "sol_1",
                "title": "Tamil Nadu Income Tax & Chennai Professional Tax — Salaried (Form 16) Complete Workflow",
                "confidence": 0.96,
                "pricing": {
                    "total_cost_tokens": 500,
                    "estimated_savings_percentage": 73,
                    "breakdown": {
                        "base_cost": 200,
                        "execution_tokens": 300,
                        "rating_discount": 0,
                    },
                },
                "coverage": ["ITR-1", "Section 80C", "Section 80D", "Section 24(b)", "Chennai PT", "Section 16(iii)"],
                "rating": 4.9,
                "usage_count": 47,
            },
            "alternatives": [
                {"solution_id": "sol_2", "title": "Generic India Income Tax Filing (ITR-1)", "confidence": 0.73},
                {"solution_id": "sol_3", "title": "Tamil Nadu Professional Tax Return only", "confidence": 0.55},
            ],
            "privacy": {
                "pii_detected": ["income_bracket"],
                "action": "bucketed to 8L-10L (exact income never sent to marketplace)",
            },
        },
        latency_ms=1200,
    ))
    step1.output = (
        "Found 3 matching workflows. Best match: 'Tamil Nadu Income Tax & Chennai Professional Tax — Salaried' — "
        "96% confidence, 500 tokens, covers ITR-1 + 80C + 80D + 24(b) + Chennai PT + Sec 16(iii) deduction. "
        "This saves ~73% vs solving from scratch. Rating: 4.9★ from 47 users."
    )
    trace.steps.append(step1)

    # ── Step 2: Agent evaluates and calls mark_buy ────────────────────────
    step2 = EnhancedStep(
        step_number=2,
        action="mark_buy",
        reasoning=(
            "The marketplace found a 96% confidence match that covers Chennai Professional Tax, "
            "Section 24(b) interest rules, and Section 16(iii) deductions — things I might "
            "miss solving from scratch. At 500 tokens with 73% savings, this is an excellent deal. "
            "It has a 4.9★ rating from 47 users. Purchasing now."
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
                "title": "Tamil Nadu Income Tax & Chennai Professional Tax — Salaried (Form 16) Complete Workflow",
                "total_steps": 10,
                "workflows": [
                    {
                        "workflow_id": "tn_salaried_tax_2024",
                        "title": "Tamil Nadu FY 2024-25 Tax Filing",
                        "steps": [
                            {"step": 1, "action": "Gather Form 16, Form 26AS, and AIS/TIS statement"},
                            {"step": 2, "action": "Identify Tamil Nadu Professional Tax deductions under Section 16(iii) (max ₹2,500/year)"},
                            {"step": 3, "action": "Complete Section 80C (PPF, EPF, ELSS, Insurance) deductions up to ₹1,50,000"},
                            {"step": 4, "action": "Complete Section 24(b) (Home loan interest) deductions up to ₹2,00,000"},
                            {"step": 5, "action": "Complete Section 80D (Medical insurance) deductions up to ₹25,000"},
                            {"step": 6, "action": "Compare: Old Tax Regime tax vs New Tax Regime tax (standard deduction ₹75,000 in New)"},
                            {"step": 7, "action": "Apply New Tax Regime slabs: ₹0-3L 0%, ₹3-6L 5%, ₹6-9L 10% (rebate under 87A if taxable income ≤ ₹7L)"},
                            {"step": 8, "action": "Reconcile TDS from W2/Form 16 and verify Chennai Professional Tax paid (₹1,250 half-yearly)"},
                            {"step": 9, "action": "Calculate final net tax liability (including 4% Health and Education Cess)"},
                            {"step": 10, "action": "File ITR-1 electronically on the Income Tax India e-filing portal"},
                        ],
                        "edge_cases": [
                            "Tamil Nadu Professional Tax is mandatory (Chennai GCC: ₹1,250/half-year) and fully deductible under Sec 16(iii) in Old Regime",
                            "Section 24(b) deduction for self-occupied home loan interest limit is ₹2,00,000 (not ₹1,00,000)",
                            "Section 87A rebate gives 100% tax waiver if taxable income under New Regime is ≤ ₹7,00,000",
                            "New Tax Regime Standard Deduction is ₹75,000 for FY 2024-25, and tax slabs are restructured",
                            "ITR-1 is suitable only if salary, one house property, and other sources are the only income streams",
                            "Health & Education Cess is flat 4% of the calculated income tax",
                        ],
                        "domain_knowledge": {
                            "new_regime_slabs_fy_2024_25": {
                                "0-300000": "0%",
                                "300001-600000": "5%",
                                "600001-900000": "10%",
                                "900001-1200000": "15%",
                                "1200001-1500000": "20%",
                                "1500001+": "30%",
                            },
                            "standard_deduction_new_regime": 75000,
                            "standard_deduction_old_regime": 50000,
                            "sec_24b_home_interest_limit": 200000,
                            "chennai_professional_tax_yearly": 2500,
                        },
                    }
                ],
            },
        },
        latency_ms=800,
    ))
    step2.output = (
        "Purchased workflow for 500 tokens. Received complete 10-step execution plan "
        "with 6 edge cases and domain knowledge including correct FY 2024-25 brackets."
    )
    trace.steps.append(step2)

    # ── Step 3: Agent presents the plan to the user ───────────────────────
    step3 = EnhancedStep(
        step_number=3,
        action="present_plan",
        reasoning=(
            "Now I have a complete, expert-verified execution plan. Let me present "
            "this to the user with all the important Tamil Nadu and India tax details highlighted."
        ),
        tokens_used=420,
        latency_ms=1100,
    )
    step3.output = (
        "Here's your complete Tamil Nadu (Chennai) tax filing plan:\n\n"
        "📋 FORMS REQUIRED:\n"
        "  • ITR-1 (Main Indian Income Tax return)\n"
        "  • Greater Chennai Corporation (GCC) Professional Tax receipt/statement\n\n"
        "💡 CRITICAL REGIONAL & REGIME DETAILS:\n"
        "  1. Chennai Professional Tax (₹2,500/year) is fully deductible under Sec 16(iii) for Old Regime\n"
        "  2. Section 24(b) limit is ₹2,00,000 for self-occupied home loan interest (baseline capped it at ₹1,00,000)\n"
        "  3. New Regime standard deduction is ₹75,000 for FY 2024-25 with restructured tax slabs\n"
        "  4. Section 87A rebate provides 100% tax waiver if taxable income in New Regime ≤ ₹7,00,000\n\n"
        "📊 REGIME COMPARISON & TAX CALCULATION (Gross Salary: ₹8,50,000):\n"
        "  • OLD REGIME:\n"
        "    Gross Salary: ₹8,50,000\n"
        "    Deductions: ₹50,000 (Std Ded) + ₹2,500 (PT) + ₹1,50,000 (80C) + ₹25,000 (80D) = ₹2,27,500\n"
        "    Taxable Income: ₹6,22,500\n"
        "    Calculated Tax: ₹37,000 + 4% Cess = ₹38,480\n"
        "  • NEW REGIME:\n"
        "    Gross Salary: ₹8,50,000\n"
        "    Deductions: ₹75,000 (Std Ded) = ₹75,000\n"
        "    Taxable Income: ₹7,75,000\n"
        "    Calculated Tax: ₹32,500 (₹3-6L: 5%, ₹6-7.75L: 10%) + 4% Cess = ₹33,800\n\n"
        "➡️ RECOMMENDATION: File under the NEW REGIME to save ₹4,680. Net tax liability is ₹33,800.\n"
        "This plan has been used by 47 other filers with a 4.9★ rating."
    )
    trace.steps.append(step3)

    # ── Step 4: Agent rates the workflow ───────────────────────────────────
    step4 = EnhancedStep(
        step_number=4,
        action="mark_rate",
        reasoning=(
            "The workflow provided accurate, complete information comparing Indian tax regimes "
            "and incorporating Chennai Professional Tax. Rating it now to help future agents."
        ),
        tokens_used=80,
        latency_ms=400,
    )
    step4.tool_calls.append(ToolCall(
        tool_name="mark_rate",
        tool_input={
            "workflow_id": "tn_salaried_tax_2024",
            "rating": 5,
        },
        result={
            "success": True,
            "workflow_id": "tn_salaried_tax_2024",
            "new_average_rating": 4.92,
            "total_ratings": 48,
        },
        latency_ms=200,
    ))
    step4.output = "Rated workflow 5★. New average: 4.92★ (48 ratings)."
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
        "✅ Verified Chennai Professional Tax (₹2,500/yr) is deductible under Sec 16(iii) (baseline missed this)",
        "✅ Applied correct Section 24(b) home loan interest cap of ₹2,00,000 (baseline used incorrect ₹1,00,000 cap)",
        "✅ Calculated and recommended the New Tax Regime which saves the taxpayer ₹4,680 (baseline ignored this)",
        "✅ Used correct FY 2024-25 New Tax Regime brackets (baseline used outdated brackets)",
        "✅ Checked Section 87A rebate eligibility (baseline ignored this)",
        "✅ Outlined mandatory professional tax slabs for Greater Chennai Corporation (baseline treated as optional)",
    ]

    return trace
