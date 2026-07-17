"""
without_marktools.py — Simulates what an agent does WITHOUT marktools.

This is the "baseline" agent: raw Claude solving a tax filing task from scratch.
It has NO access to pre-solved workflows, NO domain expertise, NO edge cases.
It has to reason through everything itself, burning tokens and making mistakes.

This file is used by the demo to show the BEFORE state.
"""

import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class BaselineStep:
    step_number: int
    action: str
    reasoning: str
    output: str
    tokens_used: int
    latency_ms: float
    correct: bool = True
    missed_edge_case: Optional[str] = None


@dataclass
class BaselineTrace:
    task: str
    steps: List[BaselineStep] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    accuracy_score: float = 0.0
    errors: List[str] = field(default_factory=list)
    missed_edge_cases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "steps": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "reasoning": s.reasoning,
                    "output": s.output,
                    "tokens_used": s.tokens_used,
                    "latency_ms": s.latency_ms,
                    "correct": s.correct,
                    "missed_edge_case": s.missed_edge_case,
                }
                for s in self.steps
            ],
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "accuracy_score": self.accuracy_score,
            "errors": self.errors,
            "missed_edge_cases": self.missed_edge_cases,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Simulated baseline: Claude solving Ohio taxes from scratch
# ──────────────────────────────────────────────────────────────────────────────

def run_baseline_agent(task: str) -> BaselineTrace:
    """
    Simulate a raw Claude agent attempting Tamil Nadu tax filing WITHOUT marktools.

    This models what actually happens when an LLM tries to do domain-specific
    tasks from scratch: it gets the broad strokes right but misses critical
    state-specific edge cases, local tax nuances, and validation rules.
    """
    trace = BaselineTrace(task=task)
    start = time.time()

    # ── Step 1: Parse the request ─────────────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=1,
        action="parse_request",
        reasoning=(
            "I need to help the user file Tamil Nadu tax returns for FY 2024-25. "
            "They have Form 16 income around ₹8,50,000, reside in Chennai, and want "
            "to maximize deductions under the Old Tax Regime. Let me think through "
            "the Indian tax filing process step by step."
        ),
        output="Parsed: state=Tamil Nadu, city=Chennai, year=FY 2024-25, income≈₹8.5L, Form 16, Old Tax Regime deductions",
        tokens_used=320,
        latency_ms=800,
        correct=True,
    ))

    # ── Step 2: Research Tamil Nadu tax forms ─────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=2,
        action="research_forms",
        reasoning=(
            "Income tax in India is filed via ITR forms. For salary income with "
            "house property and other sources, ITR-1 (Sahaj) is appropriate. "
            "I'll need to look up Tamil Nadu state-specific tax forms or local levies."
        ),
        output=(
            "Forms identified: ITR-1 (main tax return). "
            "Will calculate taxable income using standard deductions."
        ),
        tokens_used=580,
        latency_ms=1200,
        correct=True,
        missed_edge_case="Did NOT identify Tamil Nadu Professional Tax (GCC slabs) — required for salaried employees in Chennai",
    ))
    trace.missed_edge_cases.append(
        "❌ Missed Tamil Nadu Professional Tax deduction — mandatory for Chennai salaried residents"
    )

    # ── Step 3: Calculate Gross Income ────────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=3,
        action="calculate_gross_income",
        reasoning=(
            "Gross total income starts with the salary income from Form 16 of ₹8,50,000. "
            "I will assume standard deductions of ₹50,000 apply to arrive at gross taxable salary."
        ),
        output="Gross Income estimated at ₹8,50,000 (standard salary deduction of ₹50,000 to be applied later)",
        tokens_used=640,
        latency_ms=1100,
        correct=True,
    ))

    # ── Step 4: Old Regime deductions (WITH ERROR) ────────────────────────
    trace.steps.append(BaselineStep(
        step_number=4,
        action="calculate_old_regime_deductions",
        reasoning=(
            "Under the Old Tax Regime, we deduct investments like Section 80C (up to ₹1,50,000) "
            "and home loan interest under Section 24(b). "
            "Note: The Section 24(b) deduction for self-occupied property interest is capped at ₹1,00,000."
        ),
        output=(
            "Deductions calculated with ₹1,00,000 cap applied to home loan interest under Sec 24(b). "
            "Total estimated deductions: ₹2,75,000 (80C ₹1,50,000 + 80D ₹25,000 + Sec 24(b) capped at ₹1,00,000)."
        ),
        tokens_used=890,
        latency_ms=1500,
        correct=False,
        missed_edge_case=(
            "WRONG: Section 24(b) home loan interest deduction limit is actually ₹2,00,000 for self-occupied properties. "
            "The baseline agent applied an incorrect cap of ₹1,00,000, costing the taxpayer ₹1,00,000 in deductions."
        ),
    ))
    trace.errors.append(
        "🚨 Applied incorrect ₹100k cap to Section 24(b) home loan interest — actual limit is ₹200k. "
        "Taxpayer loses ₹1,00,000 in deductions. Potential cost: ₹20,000+ in overpaid tax."
    )
    trace.missed_edge_cases.append(
        "❌ Applied incorrect home loan interest limit — missed ₹1,00,000 in eligible deductions"
    )

    # ── Step 5: Tax slab calculation (WITH ERROR) ─────────────────────────
    trace.steps.append(BaselineStep(
        step_number=5,
        action="calculate_tax_slabs",
        reasoning=(
            "Let's apply the graduated tax slabs. For FY 2024-25, under the Old Tax Regime, "
            "the slabs start tax-free up to ₹2.5 Lakhs, then 5% up to ₹5 Lakhs, and 20% beyond that."
        ),
        output=(
            "Applied tax slabs: ₹37,000 estimated tax liability under Old Regime. "
            "Used old tax slabs: 0% up to ₹2.5L, 5% from ₹2.5L to ₹5L, 20% from ₹5L to ₹10L."
        ),
        tokens_used=720,
        latency_ms=1300,
        correct=False,
        missed_edge_case=(
            "Used outdated brackets. For FY 2024-25, under New Tax Regime, the "
            "slabs are much lower (₹0-3L 0%, ₹3-6L 5%, ₹6-9L 10%). The agent "
            "failed to compare and recommend the New Regime which has a standard deduction of ₹75,000."
        ),
    ))
    trace.errors.append(
        "🚨 Used outdated tax brackets and failed to compare with New Tax Regime (slabs restructured for FY 2024-25). "
        "Standard deduction in New Regime is ₹75,000. Calculated tax is sub-optimal."
    )

    # ── Step 6: Apply credits & rebates (WITH ERROR) ──────────────────────
    trace.steps.append(BaselineStep(
        step_number=6,
        action="apply_credits_rebates",
        reasoning=(
            "I should check for applicable tax rebates. Section 87A rebate applies to taxable income."
        ),
        output="No rebates or credits applied. Net tax estimated at ₹37,000.",
        tokens_used=410,
        latency_ms=900,
        correct=False,
        missed_edge_case=(
            "Missed Section 87A rebate comparison (for taxable income up to ₹7,00,000 in New Tax Regime, rebate is 100%). "
            "Also missed taking deduction of Tamil Nadu Professional Tax paid under Section 16(iii) (₹2,500)."
        ),
    ))
    trace.errors.append(
        "🚨 Missed Section 87A rebate eligibility check and Chennai Professional Tax deduction under Section 16(iii)"
    )
    trace.missed_edge_cases.append(
        "❌ Missed Tamil Nadu Professional Tax deduction (₹2,500) under Section 16(iii) for Old Regime"
    )

    # ── Step 7: Local/Professional taxes (INCOMPLETE) ────────────────────
    trace.steps.append(BaselineStep(
        step_number=7,
        action="local_taxes",
        reasoning=(
            "Tamil Nadu levies a Professional Tax. I should advise the user to contact their employer "
            "or checking local corporation tables for professional tax details."
        ),
        output=(
            "Note: Greater Chennai Corporation levies professional tax. "
            "The user should check with their payroll department if it is deducted. "
            "This is considered a municipal filing rather than a federal tax filing requirement."
        ),
        tokens_used=350,
        latency_ms=700,
        correct=False,
        missed_edge_case=(
            "Tamil Nadu Professional Tax is mandatory — salaried employees earning above ₹75,000 per half-year "
            "owe ₹1,250 half-yearly (₹2,500 per year). If the employer does not deduct it, it must be paid "
            "separately online to Greater Chennai Corporation, and claimed as deduction under Section 16(iii)."
        ),
    ))
    trace.errors.append(
        "🚨 Treated Professional Tax as optional check — it is a mandatory half-yearly levy "
        "(Chennai GCC: ₹1,250 per half-year). Must ensure employer deducted it or file online."
    )
    trace.missed_edge_cases.append(
        "❌ Dismissed Professional Tax as 'optional corporate check' — it is a mandatory municipal tax"
    )

    # ── Step 8: Filing recommendation ─────────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=8,
        action="final_recommendation",
        reasoning=(
            "Let me summarize the filing recommendation for the user."
        ),
        output=(
            "Summary: File ITR-1 under Old Regime. Estimated tax: ₹37,000 + 4% Cess = ₹38,480. "
            "Submit via Income Tax e-filing portal. Check local Professional Tax if applicable."
        ),
        tokens_used=480,
        latency_ms=1000,
        correct=False,
        missed_edge_case="Final tax estimate and regime choice are sub-optimal due to compounding errors above",
    ))

    # ── Totals ────────────────────────────────────────────────────────────
    trace.total_tokens = sum(s.tokens_used for s in trace.steps)
    trace.total_latency_ms = sum(s.latency_ms for s in trace.steps)

    # Accuracy: 3 correct out of 8 steps, plus partial credit
    correct_steps = sum(1 for s in trace.steps if s.correct)
    trace.accuracy_score = round(correct_steps / len(trace.steps) * 100, 1)

    return trace
