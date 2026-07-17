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
    Simulate a raw Claude agent attempting Ohio tax filing WITHOUT marktools.

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
            "I need to help the user file Ohio 2024 taxes. They have W2 income "
            "around $85,000 and want itemized deductions. Let me think through "
            "the Ohio tax filing process step by step."
        ),
        output="Parsed: state=Ohio, year=2024, income≈$85k, W2, itemized deductions",
        tokens_used=320,
        latency_ms=800,
        correct=True,
    ))

    # ── Step 2: Research Ohio tax forms ───────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=2,
        action="research_forms",
        reasoning=(
            "Ohio uses the IT-1040 form for state income tax. I'll need to "
            "determine which schedules are required. For itemized deductions, "
            "there should be a Schedule A equivalent."
        ),
        output=(
            "Forms identified: IT-1040 (main), Schedule A (itemized deductions). "
            "Will need to calculate Ohio AGI separately from federal AGI."
        ),
        tokens_used=580,
        latency_ms=1200,
        correct=True,
        missed_edge_case="Did NOT identify SD-100 (school district tax) — required for most Ohio filers",
    ))
    trace.missed_edge_cases.append(
        "❌ Missed SD-100 school district tax form — required for ~85% of Ohio residents"
    )

    # ── Step 3: Calculate Ohio AGI ────────────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=3,
        action="calculate_ohio_agi",
        reasoning=(
            "Ohio AGI is based on federal AGI with some state-specific adjustments. "
            "I'll assume the federal AGI is approximately equal to the W2 income of $85,000. "
            "Standard adjustments include retirement income credits and 529 contributions."
        ),
        output="Ohio AGI estimated at $85,000 (assuming no major state adjustments)",
        tokens_used=640,
        latency_ms=1100,
        correct=True,
    ))

    # ── Step 4: Itemized deductions (WITH ERROR) ──────────────────────────
    trace.steps.append(BaselineStep(
        step_number=4,
        action="calculate_itemized_deductions",
        reasoning=(
            "For itemized deductions, I need to consider mortgage interest, "
            "property taxes, charitable contributions, and medical expenses. "
            "Note: The federal SALT cap of $10,000 applies to property tax deductions."
        ),
        output=(
            "Itemized deductions calculated with $10,000 SALT cap applied to property taxes. "
            "Total estimated itemized: $14,200 (mortgage $8,500 + property tax capped at $10,000... "
            "wait, the cap is for ALL state/local taxes combined, so property tax + state income tax ≤ $10,000)"
        ),
        tokens_used=890,
        latency_ms=1500,
        correct=False,
        missed_edge_case=(
            "WRONG: Ohio does NOT have the $10,000 SALT cap. "
            "The federal cap exists but Ohio allows FULL property tax deduction on the state return. "
            "This error could cost the taxpayer $2,000+ in missed deductions."
        ),
    ))
    trace.errors.append(
        "🚨 Applied federal $10k SALT cap to Ohio state return — Ohio has NO SALT cap. "
        "Full property tax is deductible on IT-1040. Potential cost: $2,000+ in overpaid tax."
    )
    trace.missed_edge_cases.append(
        "❌ Applied SALT cap incorrectly — Ohio allows full property tax deduction"
    )

    # ── Step 5: Tax bracket calculation ───────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=5,
        action="calculate_tax",
        reasoning=(
            "Ohio has graduated tax brackets. For 2024, the rates range from about "
            "0.5% to 4%. Let me apply the brackets to the taxable income."
        ),
        output=(
            "Applied Ohio tax brackets: ~$2,350 estimated Ohio income tax. "
            "Used rates: 0%-$25,000 at 0.5%, $25,001-$100,000 at 2.5%, over $100,000 at 3.5%"
        ),
        tokens_used=720,
        latency_ms=1300,
        correct=False,
        missed_edge_case=(
            "Used OUTDATED brackets. 2024 Ohio brackets are: "
            "$0-$26,050 at 0%, $26,051-$100,000 at 2.765%, $100,001-$115,300 at 3.226%, "
            "$115,301+ at 3.688%. The 0% bracket especially matters — first $26k is tax-free."
        ),
    ))
    trace.errors.append(
        "🚨 Used outdated tax brackets — Ohio restructured brackets for 2024. "
        "First $26,050 is now TAX-FREE (0% rate). Calculated tax is wrong."
    )

    # ── Step 6: Credits ───────────────────────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=6,
        action="apply_credits",
        reasoning=(
            "I should check for applicable Ohio tax credits. The main ones are "
            "the earned income credit and retirement income credit."
        ),
        output="Applied earned income credit. No other credits identified.",
        tokens_used=410,
        latency_ms=900,
        correct=False,
        missed_edge_case=(
            "Missed Joint Filing Credit ($650 for married filing jointly — AUTOMATIC). "
            "Also missed checking for local tax credits."
        ),
    ))
    trace.errors.append(
        "🚨 Missed $650 Joint Filing Credit — automatic for all MFJ Ohio filers"
    )
    trace.missed_edge_cases.append(
        "❌ Missed Joint Filing Credit ($650) — automatic for married filing jointly"
    )

    # ── Step 7: Local taxes (INCOMPLETE) ──────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=7,
        action="local_taxes",
        reasoning=(
            "Ohio may have local income taxes. I should mention that the user "
            "may need to check their local municipality for additional tax requirements."
        ),
        output=(
            "Note: Some Ohio municipalities levy local income taxes. "
            "The user should check their local tax rate. This is outside the scope "
            "of state filing."
        ),
        tokens_used=350,
        latency_ms=700,
        correct=False,
        missed_edge_case=(
            "Ohio local taxes are NOT optional — nearly all Ohio cities/school districts "
            "levy income tax. Columbus is 2.5%. This is a REQUIRED filing, not a 'maybe check'. "
            "Should have identified RITA/CCA filing requirement and work-city vs residence-city rules."
        ),
    ))
    trace.errors.append(
        "🚨 Treated local taxes as optional — Ohio local income tax is mandatory "
        "for most residents (Columbus: 2.5%). Should file city return via RITA/CCA."
    )
    trace.missed_edge_cases.append(
        "❌ Dismissed local taxes as 'optional' — they are mandatory for most Ohio cities"
    )

    # ── Step 8: Filing recommendation ─────────────────────────────────────
    trace.steps.append(BaselineStep(
        step_number=8,
        action="final_recommendation",
        reasoning=(
            "Let me summarize the filing recommendation for the user."
        ),
        output=(
            "Summary: File IT-1040 with itemized deductions. Estimated Ohio tax: ~$2,350. "
            "Use Ohio eFile to submit electronically. Consider checking local tax requirements."
        ),
        tokens_used=480,
        latency_ms=1000,
        correct=False,
        missed_edge_case="Final tax estimate is wrong due to compounding errors above",
    ))

    # ── Totals ────────────────────────────────────────────────────────────
    trace.total_tokens = sum(s.tokens_used for s in trace.steps)
    trace.total_latency_ms = sum(s.latency_ms for s in trace.steps)

    # Accuracy: 3 correct out of 8 steps, plus partial credit
    correct_steps = sum(1 for s in trace.steps if s.correct)
    trace.accuracy_score = round(correct_steps / len(trace.steps) * 100, 1)

    return trace
