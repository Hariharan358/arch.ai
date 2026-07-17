'use client'

import { useEffect, useState } from 'react'
import styles from './page.module.css'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

function CodeBlock({ code, filename }: { code: string; filename?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className={styles.codeWrapper}>
      <div className={styles.codeBar}>
        <span>{filename || ''}</span>
        <button
          className={styles.copyBtn}
          onClick={() => {
            navigator.clipboard.writeText(code)
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
          }}
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className={styles.codeBlock}>{code}</pre>
    </div>
  )
}

const TABS = [
  { id: 'quickstart', label: 'Quick Start' },
  { id: 'anthropic', label: 'Anthropic' },
  { id: 'openai', label: 'OpenAI' },
  { id: 'client', label: 'Client' },
  { id: 'tools', label: 'Tools' },
  { id: 'models', label: 'Models' },
]

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState('quickstart')
  const [tools, setTools] = useState<any[]>([])

  useEffect(() => {
    fetch(`${API}/api/sdk/tools`).then(r => r.json()).then(d => setTools(d.tools || [])).catch(() => {})
  }, [])

  return (
    <>
      <Nav />
      <main className={styles.main}>
        <div className={styles.header}>
          <div className={styles.badge}>Documentation</div>
          <h1>archaitools</h1>
          <p className={styles.subtitle}>
            The Python SDK that lets AI agents buy pre-solved reasoning workflows.
          </p>
          <div className={styles.installRow}>
            <code className={styles.installCode}>pip install archaitools</code>
          </div>
        </div>

        <div className={styles.layout}>
          {/* Sidebar nav */}
          <nav className={styles.sidebar}>
            {TABS.map(tab => (
              <button
                key={tab.id}
                className={`${styles.sidebarItem} ${activeTab === tab.id ? styles.sidebarActive : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {/* Content */}
          <div className={styles.content} key={activeTab}>
            {activeTab === 'quickstart' && (
              <div className={styles.section}>
                <h2>Quick Start</h2>
                <p>Get started with archaitools in 3 lines of code.</p>

                <h3>Installation</h3>
                <CodeBlock filename="terminal" code={`pip install archaitools

# With framework extras
pip install archaitools[anthropic]   # Anthropic Claude support
pip install archaitools[openai]      # OpenAI GPT support
pip install archaitools[all]         # All frameworks`} />

                <h3>Basic Usage</h3>
                <CodeBlock filename="main.py" code={`from archaitools import MarkClient

mark = MarkClient(api_key="mk_...")  # or set MARK_API_KEY env var

# 1. Estimate — is the marketplace worth it? (free, no credits)
estimate = mark.estimate("File Ohio 2024 taxes with W2 and itemized deductions")

# 2. Buy — purchase the best solution
receipt = mark.buy(estimate.session_id, estimate.best_solution.solution_id)

# 3. Use — step-by-step instructions, edge cases, domain knowledge
for wf in receipt.execution_plan.workflows:
    print(f"  {wf.workflow_title}")
    for step in wf.workflow.steps:
        print(f"  Step {step['step']}: {step['thought']}")`} />

                <h3>One-Shot Solve</h3>
                <CodeBlock code={`# Auto-estimate + auto-buy the best solution in one call
receipt = mark.solve("File Ohio 2024 taxes with W2 and itemized deductions")
print(f"Tokens charged: {receipt.tokens_charged}")`} />

                <h3>Environment Variables</h3>
                <table className={styles.table}>
                  <thead>
                    <tr><th>Variable</th><th>Description</th><th>Default</th></tr>
                  </thead>
                  <tbody>
                    <tr><td><code>MARK_API_KEY</code></td><td>Your API key</td><td>—</td></tr>
                    <tr><td><code>MARK_API_URL</code></td><td>API base URL</td><td><code>https://api.mark.ai</code></td></tr>
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'anthropic' && (
              <div className={styles.section}>
                <h2>Use with Anthropic Claude</h2>
                <p>
                  archaitools provides native Anthropic tool_use format. Claude can autonomously
                  search, buy, and rate marketplace workflows.
                </p>
                <CodeBlock filename="basic.py" code={`from archaitools import MarkTools
from anthropic import Anthropic

mark = MarkTools(api_key="mk_...")
client = Anthropic()

# Pass Mark tools alongside your own tools
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=mark.to_anthropic(),
    messages=[{"role": "user", "content": "Help me file my Ohio taxes for 2024"}],
)

# Handle tool calls in your agent loop
for block in response.content:
    if block.type == "tool_use":
        result = mark.execute(block.name, block.input)
        # Return result to Claude as tool_result`} />

                <h3>Full Agent Loop</h3>
                <CodeBlock filename="agent.py" code={`from archaitools import MarkTools
from anthropic import Anthropic

mark = MarkTools(api_key="mk_...")
client = Anthropic()
messages = [{"role": "user", "content": "Help me file my Ohio taxes"}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        tools=mark.to_anthropic(),
        messages=messages,
    )

    if response.stop_reason == "tool_use":
        assistant_content = []
        tool_results = []

        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use", "id": block.id,
                    "name": block.name, "input": block.input
                })
                result = mark.execute(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})
    else:
        print(response.content[0].text)
        break`} />
              </div>
            )}

            {activeTab === 'openai' && (
              <div className={styles.section}>
                <h2>Use with OpenAI GPT-4</h2>
                <p>
                  archaitools generates OpenAI-compatible function calling definitions.
                  Works with GPT-4o, GPT-4, and any model that supports function calling.
                </p>
                <CodeBlock filename="openai_agent.py" code={`from archaitools import MarkTools
from openai import OpenAI
import json

mark = MarkTools(api_key="mk_...")
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    tools=mark.to_openai(),
    messages=[{"role": "user", "content": "Help me file my Ohio taxes"}],
)

# Execute tool calls
for call in response.choices[0].message.tool_calls or []:
    result = mark.execute(
        call.function.name,
        json.loads(call.function.arguments)
    )
    print(f"Tool: {call.function.name}")
    print(f"Result: {result[:200]}")`} />
              </div>
            )}

            {activeTab === 'client' && (
              <div className={styles.section}>
                <h2>MarkClient Reference</h2>
                <p>The core HTTP client for direct API access.</p>

                <h3>Initialization</h3>
                <CodeBlock code={`from archaitools import MarkClient

# API key from parameter
mark = MarkClient(api_key="mk_...")

# API key from environment
# export MARK_API_KEY=mk_...
mark = MarkClient()

# Custom server (self-hosted)
mark = MarkClient(base_url="http://localhost:5001")`} />

                <h3>Methods</h3>
                <table className={styles.table}>
                  <thead>
                    <tr><th>Method</th><th>Cost</th><th>Description</th></tr>
                  </thead>
                  <tbody>
                    <tr><td><code>estimate(query)</code></td><td>Free</td><td>Search and get ranked solutions with pricing</td></tr>
                    <tr><td><code>buy(session_id, solution_id)</code></td><td>Credits</td><td>Purchase solution, get full execution plan</td></tr>
                    <tr><td><code>rate(workflow_id, rating)</code></td><td>Free</td><td>Rate a workflow after use</td></tr>
                    <tr><td><code>search(**filters)</code></td><td>Free</td><td>Search marketplace with filters</td></tr>
                    <tr><td><code>solve(query)</code></td><td>Credits</td><td>One-shot: estimate + buy best solution</td></tr>
                    <tr><td><code>balance()</code></td><td>Free</td><td>Check credit balance</td></tr>
                    <tr><td><code>sanitize(data)</code></td><td>Free</td><td>Preview PII sanitization</td></tr>
                    <tr><td><code>health()</code></td><td>Free</td><td>API health check</td></tr>
                    <tr><td><code>chat(message)</code></td><td>Free</td><td>Talk to the Claude agent</td></tr>
                    <tr><td><code>list_workflows()</code></td><td>Free</td><td>List all available workflows</td></tr>
                  </tbody>
                </table>

                <h3>Privacy Sanitization</h3>
                <CodeBlock filename="privacy.py" code={`result = mark.sanitize({
    "name": "John Smith",         # removed
    "ssn": "123-45-6789",         # removed
    "exact_income": 87432.18,     # bucketed to "80k-100k"
    "state": "ohio",              # kept
    "year": 2024,                 # kept
})
# public_query: {"state": "ohio", "year": 2024, "exact_income": "80k-100k"}
# private_data: {"name": "John Smith", "ssn": "123-45-6789"}`} />
              </div>
            )}

            {activeTab === 'tools' && (
              <div className={styles.section}>
                <h2>Tool Definitions</h2>
                <p>archaitools exposes 4 tools that AI agents can call:</p>

                {tools.length > 0 ? (
                  tools.map((tool: any, i: number) => (
                    <div key={i} className={styles.toolDef}>
                      <h3>{tool.name}</h3>
                      <p>{tool.description}</p>
                      <CodeBlock code={JSON.stringify(tool.input_schema, null, 2)} />
                    </div>
                  ))
                ) : (
                  <>
                    <div className={styles.toolDef}>
                      <h3>mark_estimate</h3>
                      <p>Search the marketplace and get pricing. Free, no credits spent.</p>
                      <CodeBlock code={`{
  "query": "string (required) — task description",
  "context": "object (optional) — metadata, PII auto-sanitized"
}`} />
                    </div>
                    <div className={styles.toolDef}>
                      <h3>mark_buy</h3>
                      <p>Purchase a solution. Returns full execution plan.</p>
                      <CodeBlock code={`{
  "session_id": "string (required) — from mark_estimate",
  "solution_id": "string (required) — e.g. 'sol_1'"
}`} />
                    </div>
                    <div className={styles.toolDef}>
                      <h3>mark_rate</h3>
                      <p>Rate a workflow after use.</p>
                      <CodeBlock code={`{
  "workflow_id": "string (required)",
  "rating": "integer (1-5)",
  "vote": "'up' | 'down'"
}`} />
                    </div>
                    <div className={styles.toolDef}>
                      <h3>mark_search</h3>
                      <p>Browse marketplace with filters.</p>
                      <CodeBlock code={`{
  "query": "string — search text",
  "task_type": "string — category filter",
  "state": "string — US state",
  "year": "integer"
}`} />
                    </div>
                  </>
                )}

                <h3>Format Conversion</h3>
                <CodeBlock code={`from archaitools import MarkTools

tools = MarkTools(api_key="mk_...")

tools.to_anthropic()     # Anthropic Claude format
tools.to_openai()        # OpenAI function calling format
tools.to_langchain()     # LangChain format
tools.to_json_schema()   # Raw JSON schema`} />
              </div>
            )}

            {activeTab === 'models' && (
              <div className={styles.section}>
                <h2>Response Models</h2>
                <p>All API responses are typed Pydantic models with full IDE autocomplete.</p>

                <CodeBlock filename="models.py" code={`from archaitools import (
    Workflow,           # Marketplace workflow template
    Solution,           # Ranked solution candidate
    EstimateResult,     # Response from estimate()
    PurchaseReceipt,    # Response from buy()
    RateResult,         # Response from rate()
    SearchResult,       # Search result with score
    Subtask,            # Decomposed subtask
)`} />

                <h3>Workflow</h3>
                <CodeBlock code={`workflow.workflow_id     # "ohio_w2_itemized_2024"
workflow.title           # "Ohio 2024 IT-1040 (W2, Itemized)"
workflow.total_cost      # 1000 (download_cost + execution_cost)
workflow.rating          # 4.8
workflow.num_steps       # 10
workflow.steps           # [{"step": 1, "thought": "...", "action": "..."}]
workflow.edge_cases      # ["If city has multiple jurisdictions..."]
workflow.domain_knowledge  # ["Ohio does NOT have $10k SALT cap..."]`} />

                <h3>EstimateResult</h3>
                <CodeBlock code={`estimate.session_id          # "sess_abc123" — use in buy()
estimate.num_solutions       # 3
estimate.best_solution       # Solution with rank=1
estimate.cheapest_solution   # Solution with lowest cost
estimate.solutions[0].pricing.total_cost_tokens    # 500
estimate.solutions[0].pricing.savings_percentage   # 70`} />

                <h3>PurchaseReceipt</h3>
                <CodeBlock code={`receipt.purchase_id          # "purchase_abc123"
receipt.tokens_charged       # 500
receipt.execution_plan.workflows[0].workflow_title  # "Ohio Tax Filing"
receipt.execution_plan.workflows[0].workflow.steps  # [...]
receipt.execution_plan.execution_order              # ["subtask_0", ...]`} />
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
