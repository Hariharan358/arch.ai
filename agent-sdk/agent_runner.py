"""
agent_runner.py — Base framework for running Claude agents with marktools.

Provides:
  - MarkAgent: autonomous agent loop with tool_use
  - Rich terminal output with step-by-step logging
  - Metrics collection (tokens, latency, tool calls)
  - Simulation mode (records full trace for frontend replay)

This is the core that all demo agents use.
"""

import os
import json
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from anthropic import Anthropic

from archaitools import MarkTools


# ──────────────────────────────────────────────────────────────────────────────
# Data structures for traces
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    """Record of a single tool invocation."""
    tool_name: str
    tool_input: Dict[str, Any]
    result: str
    latency_ms: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentStep:
    """One turn in the agent loop (may contain multiple tool calls)."""
    step_number: int
    thinking: str  # Claude's text reasoning
    tool_calls: List[ToolCall] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class AgentTrace:
    """Full trace of an agent run — used for frontend replay."""
    agent_name: str
    task: str
    model: str
    steps: List[AgentStep] = field(default_factory=list)
    final_response: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    tools_called: Dict[str, int] = field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        tool_summary = ", ".join(f"{k}: {v}x" for k, v in self.tools_called.items())
        return (
            f"Agent: {self.agent_name}\n"
            f"Task: {self.task}\n"
            f"Model: {self.model}\n"
            f"Steps: {len(self.steps)}\n"
            f"Tools: {tool_summary}\n"
            f"Tokens: {self.total_input_tokens} in / {self.total_output_tokens} out\n"
            f"Latency: {self.total_latency_ms:.0f}ms\n"
            f"Success: {'✅' if self.success else '❌'}\n"
        )


# ──────────────────────────────────────────────────────────────────────────────
# System prompts
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_SYSTEM = """You are an autonomous AI agent with access to the Mark AI marketplace.

Your tools:
- mark_estimate: Search for pre-solved workflows. FREE. Always call this first.
- mark_buy: Purchase the best solution. Costs credits.
- mark_rate: Rate a workflow after use. Helps the marketplace.

Workflow:
1. Understand the user's task
2. Call mark_estimate to see if the marketplace has relevant solutions
3. If relevant, call mark_buy to purchase the best solution
4. Present the execution plan to the user
5. Call mark_rate to provide feedback

Be specific. Be efficient. Explain your reasoning at every step."""


# ──────────────────────────────────────────────────────────────────────────────
# MarkAgent — the autonomous agent loop
# ──────────────────────────────────────────────────────────────────────────────

class MarkAgent:
    """
    Autonomous Claude agent that uses marktools for tool execution.

    Implements the full Anthropic tool_use loop:
      1. Send messages to Claude
      2. If Claude returns tool_use blocks, execute them via marktools
      3. Return tool_result to Claude
      4. Repeat until Claude gives a final text response

    Args:
        name: Agent identifier (for traces/logging).
        system_prompt: Custom system prompt (or uses DEFAULT_SYSTEM).
        model: Claude model to use.
        max_turns: Maximum agent loop iterations (safety limit).
        mark_api_url: Mark API base URL.
        mark_api_key: Mark API key.
        verbose: Print step-by-step output.
    """

    def __init__(
        self,
        name: str = "mark-agent",
        system_prompt: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 10,
        mark_api_url: Optional[str] = None,
        mark_api_key: Optional[str] = None,
        verbose: bool = True,
    ):
        self.name = name
        self.system_prompt = system_prompt or DEFAULT_SYSTEM
        self.model = model
        self.max_turns = max_turns
        self.verbose = verbose

        # Anthropic client
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = Anthropic(api_key=api_key) if api_key else None

        # marktools
        self.mark = MarkTools(
            api_key=mark_api_key or os.environ.get("MARK_API_KEY", ""),
            base_url=mark_api_url or os.environ.get("MARK_API_URL", "http://localhost:5001"),
        )

    def run(self, task: str) -> AgentTrace:
        """
        Execute the full autonomous agent loop for a given task.

        Returns an AgentTrace with full step-by-step recording.
        """
        trace = AgentTrace(agent_name=self.name, task=task, model=self.model)
        start_time = time.time()

        messages = [{"role": "user", "content": task}]
        tools = self.mark.to_anthropic()

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🤖 Agent: {self.name}")
            print(f"📋 Task: {task}")
            print(f"🧠 Model: {self.model}")
            print(f"{'='*60}\n")

        step_num = 0

        for turn in range(self.max_turns):
            step_num += 1
            step_start = time.time()

            if self.verbose:
                print(f"  ╭─ Step {step_num} {'─'*45}")

            # Call Claude
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=tools,
                    messages=messages,
                )
            except Exception as e:
                trace.error = str(e)
                if self.verbose:
                    print(f"  │ ❌ API Error: {e}")
                break

            trace.total_input_tokens += response.usage.input_tokens
            trace.total_output_tokens += response.usage.output_tokens

            # Parse response
            thinking = ""
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    thinking += block.text
                elif block.type == "tool_use":
                    tool_uses.append(block)

            step = AgentStep(step_number=step_num, thinking=thinking)

            if thinking and self.verbose:
                # Truncate for display
                display = thinking[:300] + ("..." if len(thinking) > 300 else "")
                print(f"  │ 💭 {display}")

            # If no tool calls, this is the final response
            if response.stop_reason == "end_turn" or not tool_uses:
                step.latency_ms = (time.time() - step_start) * 1000
                trace.steps.append(step)
                trace.final_response = thinking
                trace.success = True

                if self.verbose:
                    print(f"  │ ✅ Final response ({len(thinking)} chars)")
                    print(f"  ╰{'─'*55}\n")
                break

            # Execute tool calls
            assistant_content = response.content
            tool_results = []

            for tool_use in tool_uses:
                tc_start = time.time()
                tool_name = tool_use.name
                tool_input = tool_use.input

                if self.verbose:
                    input_preview = json.dumps(tool_input, indent=None)[:100]
                    print(f"  │ 🔧 {tool_name}({input_preview})")

                # Execute via marktools
                try:
                    result = self.mark.execute(tool_name, tool_input)
                except Exception as e:
                    result = json.dumps({"error": str(e)})

                tc_latency = (time.time() - tc_start) * 1000

                # Record
                tc = ToolCall(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    result=result[:2000],  # cap for trace size
                    latency_ms=tc_latency,
                )
                step.tool_calls.append(tc)
                trace.tools_called[tool_name] = trace.tools_called.get(tool_name, 0) + 1

                if self.verbose:
                    result_preview = result[:150] + ("..." if len(result) > 150 else "")
                    print(f"  │   → {result_preview}")
                    print(f"  │   ⏱ {tc_latency:.0f}ms")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })

            # Build messages for next turn
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

            step.latency_ms = (time.time() - step_start) * 1000
            trace.steps.append(step)

            if self.verbose:
                print(f"  ╰{'─'*55}\n")

        trace.total_latency_ms = (time.time() - start_time) * 1000

        if self.verbose:
            print(f"\n{'='*60}")
            print(trace.summary())
            print(f"{'='*60}\n")

        return trace


# ──────────────────────────────────────────────────────────────────────────────
# Simulated agent (no API key needed — for frontend demos)
# ──────────────────────────────────────────────────────────────────────────────

class SimulatedAgent:
    """
    Simulated agent that produces realistic traces WITHOUT calling Claude.
    Used by the frontend /sdk page to show agent behavior.
    """

    def __init__(self, name: str = "mark-agent"):
        self.name = name

    def simulate(self, scenario: dict) -> AgentTrace:
        """Generate a realistic trace from a pre-defined scenario."""
        trace = AgentTrace(
            agent_name=self.name,
            task=scenario["task"],
            model="claude-sonnet-4-20250514",
        )

        for i, step_data in enumerate(scenario["steps"]):
            step = AgentStep(step_number=i + 1, thinking=step_data["thinking"])

            for tc_data in step_data.get("tool_calls", []):
                tc = ToolCall(
                    tool_name=tc_data["tool"],
                    tool_input=tc_data["input"],
                    result=json.dumps(tc_data["result"]),
                    latency_ms=tc_data.get("latency_ms", 150),
                )
                step.tool_calls.append(tc)
                trace.tools_called[tc_data["tool"]] = trace.tools_called.get(tc_data["tool"], 0) + 1

            step.latency_ms = step_data.get("latency_ms", 800)
            trace.steps.append(step)

        trace.final_response = scenario.get("final_response", "")
        trace.total_input_tokens = scenario.get("input_tokens", 2500)
        trace.total_output_tokens = scenario.get("output_tokens", 1800)
        trace.total_latency_ms = scenario.get("total_latency_ms", 4500)
        trace.success = True

        return trace
