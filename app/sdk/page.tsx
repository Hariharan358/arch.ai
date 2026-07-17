'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import styles from './sdk.module.css'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

interface ToolCall {
  tool_name: string
  tool_input: Record<string, any>
  result: string
  latency_ms: number
}

interface AgentStep {
  step_number: number
  thinking: string
  tool_calls: ToolCall[]
  latency_ms: number
}

interface AgentTrace {
  agent_name: string
  task: string
  model: string
  steps: AgentStep[]
  final_response: string
  total_input_tokens: number
  total_output_tokens: number
  total_latency_ms: number
  tools_called: Record<string, number>
  success: boolean
}

interface Scenario {
  id: string
  title: string
  description: string
  icon: string
  task: string
}

const FALLBACK_SCENARIOS: Scenario[] = [
  {
    id: 'tax_filing',
    title: 'Ohio Tax Filing',
    description: 'Agent finds and purchases a tax workflow, then presents a step-by-step filing plan.',
    icon: '📋',
    task: 'Help me file my Ohio 2024 taxes. I have a W2 and want to use itemized deductions. Income around $85,000.',
  },
  {
    id: 'shopping',
    title: 'Smart Product Comparison',
    description: 'Agent finds a product comparison workflow, purchases it, and delivers structured recommendations.',
    icon: '🛒',
    task: 'I need to buy a laptop for software development, budget $1500-2000. Need 32GB RAM and a good screen.',
  },
  {
    id: 'orchestrator',
    title: 'Multi-Task Orchestration',
    description: 'Agent decomposes a complex relocation task into subtasks and chains marketplace workflows.',
    icon: '🔗',
    task: "I'm relocating from California to Ohio. Help with: 1) CA partial-year taxes, 2) Ohio tax setup, 3) Finding neighborhoods in Columbus.",
  },
]

/** Simple markdown-to-JSX: handles **bold**, `code`, headers, lists, paragraphs */
function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let listBuffer: string[] = []

  const flushList = () => {
    if (listBuffer.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className={styles.mdList}>
          {listBuffer.map((item, i) => (
            <li key={i}>{renderInline(item)}</li>
          ))}
        </ul>
      )
      listBuffer = []
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // Headers
    if (line.startsWith('### ')) {
      flushList()
      elements.push(<h4 key={i} className={styles.mdH4}>{renderInline(line.slice(4))}</h4>)
    } else if (line.startsWith('## ')) {
      flushList()
      elements.push(<h3 key={i} className={styles.mdH3}>{renderInline(line.slice(3))}</h3>)
    } else if (line.startsWith('# ')) {
      flushList()
      elements.push(<h2 key={i} className={styles.mdH2}>{renderInline(line.slice(2))}</h2>)
    }
    // List items
    else if (/^[-*•]\s/.test(line) || /^\d+[.)]\s/.test(line)) {
      const content = line.replace(/^[-*•]\s|^\d+[.)]\s/, '')
      listBuffer.push(content)
    }
    // Empty line
    else if (line.trim() === '') {
      flushList()
    }
    // Regular paragraph
    else {
      flushList()
      elements.push(<p key={i} className={styles.mdP}>{renderInline(line)}</p>)
    }
  }
  flushList()
  return elements
}

/** Inline markdown: **bold**, `code` */
function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = []
  const regex = /(\*\*(.+?)\*\*|`(.+?)`)/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    if (match[2]) {
      parts.push(<strong key={match.index}>{match[2]}</strong>)
    } else if (match[3]) {
      parts.push(<code key={match.index} className={styles.mdCode}>{match[3]}</code>)
    }
    lastIndex = regex.lastIndex
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }
  return parts.length === 1 ? parts[0] : parts
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      className={styles.copyBtn}
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export default function SDKPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>(FALLBACK_SCENARIOS)
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null)
  const [trace, setTrace] = useState<AgentTrace | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [visibleSteps, setVisibleSteps] = useState(0)
  const [showFinal, setShowFinal] = useState(false)
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set())
  const traceRef = useRef<HTMLDivElement>(null)
  const cancelRef = useRef(false)

  useEffect(() => {
    fetch(`${API}/api/sdk/scenarios`)
      .then(r => r.json())
      .then(data => {
        if (data.scenarios?.length > 0) setScenarios(data.scenarios)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    return () => { cancelRef.current = true }
  }, [])

  const runSimulation = useCallback(async (scenarioId: string) => {
    cancelRef.current = false
    setSelectedScenario(scenarioId)
    setTrace(null)
    setVisibleSteps(0)
    setShowFinal(false)
    setExpandedTools(new Set())
    setIsPlaying(true)

    try {
      const res = await fetch(`${API}/api/sdk/simulate/${scenarioId}`)
      const data: AgentTrace = await res.json()
      if (cancelRef.current) return
      setTrace(data)

      // Animate steps with staggered timing
      for (let i = 0; i < data.steps.length; i++) {
        if (cancelRef.current) return
        await new Promise<void>(resolve => {
          setTimeout(() => {
            setVisibleSteps(i + 1)
            resolve()
          }, 400 + Math.min(i * 350, 1200))
        })
      }

      // Show final response after a beat
      if (!cancelRef.current) {
        await new Promise(r => setTimeout(r, 500))
        setShowFinal(true)
        setIsPlaying(false)
      }
    } catch {
      setIsPlaying(false)
    }
  }, [])

  const toggleTool = (key: string) => {
    setExpandedTools(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const formatJson = (str: string) => {
    try { return JSON.stringify(JSON.parse(str), null, 2) }
    catch { return str }
  }

  const totalSteps = trace?.steps.length ?? 0
  const progress = totalSteps > 0 ? (visibleSteps / totalSteps) * 100 : 0

  return (
    <>
      <Nav />
      <main className={styles.main}>
        {/* Hero */}
        <div className={styles.hero}>
          <div className={styles.heroBadge}>Agent SDK</div>
          <h1 className={styles.heroTitle}>
            Watch agents <span className={styles.heroAccent}>think</span>
          </h1>
          <p className={styles.heroSub}>
            Live simulations of Claude agents autonomously searching, purchasing, and executing
            marketplace workflows via <code>archaitools</code>.
          </p>
        </div>

        {/* Architecture */}
        <div className={styles.arch}>
          <div className={styles.archFlow}>
            <div className={styles.archChip}>
              <span className={styles.archChipIcon}>{'>'}_</span>
              <div>
                <div className={styles.archChipTitle}>Your Agent</div>
                <div className={styles.archChipSub}>Claude / GPT-4o</div>
              </div>
            </div>
            <div className={styles.archConnector}>
              <div className={styles.archLine} />
              <span className={styles.archConnLabel}>tool_use</span>
            </div>
            <div className={styles.archChip}>
              <span className={styles.archChipIcon}>mk</span>
              <div>
                <div className={styles.archChipTitle}>archaitools</div>
                <div className={styles.archChipSub}>pip install archaitools</div>
              </div>
            </div>
            <div className={styles.archConnector}>
              <div className={styles.archLine} />
              <span className={styles.archConnLabel}>HTTPS</span>
            </div>
            <div className={styles.archChip}>
              <span className={styles.archChipIcon}>{'{ }'}</span>
              <div>
                <div className={styles.archChipTitle}>arch.ai API</div>
                <div className={styles.archChipSub}>Search + Commerce</div>
              </div>
            </div>
          </div>
        </div>

        {/* Scenario Picker */}
        <section className={styles.scenarios}>
          <div className={styles.sectionLabel}>Choose a simulation</div>
          <div className={styles.scenarioGrid}>
            {scenarios.map(s => (
              <button
                key={s.id}
                className={`${styles.scenarioCard} ${selectedScenario === s.id ? styles.scenarioActive : ''}`}
                onClick={() => {
                  runSimulation(s.id)
                  setTimeout(() => traceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300)
                }}
                disabled={isPlaying}
              >
                <span className={styles.scenarioIcon}>{s.icon}</span>
                <div>
                  <div className={styles.scenarioTitle}>{s.title}</div>
                  <div className={styles.scenarioDesc}>{s.description}</div>
                </div>
                {selectedScenario === s.id && isPlaying && (
                  <span className={styles.scenarioLive}>LIVE</span>
                )}
              </button>
            ))}
          </div>
        </section>

        {/* Trace Viewer */}
        <section ref={traceRef} className={styles.trace}>
          {trace ? (
            <div className={styles.traceWindow}>
              {/* Top bar */}
              <div className={styles.traceBar}>
                <div className={styles.traceBarLeft}>
                  <div className={styles.traceDots}>
                    <span /><span /><span />
                  </div>
                  <span className={styles.traceBarTitle}>agent-trace — {trace.model}</span>
                </div>
                <div className={styles.traceBarRight}>
                  <span>{(trace.total_latency_ms / 1000).toFixed(1)}s</span>
                  <span>{trace.total_input_tokens.toLocaleString()} in</span>
                  <span>{trace.total_output_tokens.toLocaleString()} out</span>
                </div>
              </div>

              {/* Progress bar */}
              {isPlaying && (
                <div className={styles.progressTrack}>
                  <div className={styles.progressFill} style={{ width: `${progress}%` }} />
                </div>
              )}

              {/* Task */}
              <div className={styles.traceTask}>
                <span className={styles.traceTaskLabel}>$</span>
                <span className={styles.traceTaskText}>{trace.task}</span>
              </div>

              {/* Steps timeline */}
              <div className={styles.timeline}>
                {trace.steps.slice(0, visibleSteps).map((step, idx) => (
                  <div key={idx} className={styles.timelineStep} style={{ animationDelay: `${idx * 50}ms` }}>
                    <div className={styles.timelineGutter}>
                      <div className={`${styles.timelineDot} ${idx === visibleSteps - 1 && isPlaying ? styles.timelineDotPulse : ''}`} />
                      {idx < totalSteps - 1 && <div className={styles.timelineLine} />}
                    </div>
                    <div className={styles.timelineContent}>
                      <div className={styles.stepMeta}>
                        <span className={styles.stepBadge}>Step {step.step_number}</span>
                        <span className={styles.stepTime}>{step.latency_ms}ms</span>
                      </div>

                      {/* Thinking */}
                      <div className={styles.thinkBox}>
                        <div className={styles.thinkLabel}>Reasoning</div>
                        <p className={styles.thinkText}>{step.thinking}</p>
                      </div>

                      {/* Tool calls */}
                      {step.tool_calls.map((tc, tcIdx) => {
                        const key = `${idx}-${tcIdx}`
                        const isExpanded = expandedTools.has(key)
                        return (
                          <div key={tcIdx} className={styles.toolPill}>
                            <button className={styles.toolPillHead} onClick={() => toggleTool(key)}>
                              <div className={styles.toolPillLeft}>
                                <span className={styles.toolPillIcon}>&#9889;</span>
                                <span className={styles.toolPillName}>{tc.tool_name}</span>
                                <span className={styles.toolPillMs}>{tc.latency_ms}ms</span>
                              </div>
                              <span className={styles.toolPillChevron}>{isExpanded ? '−' : '+'}</span>
                            </button>
                            {isExpanded && (
                              <div className={styles.toolPillBody}>
                                <div className={styles.toolBlock}>
                                  <div className={styles.toolBlockLabel}>Input</div>
                                  <pre>{JSON.stringify(tc.tool_input, null, 2)}</pre>
                                </div>
                                <div className={styles.toolBlock}>
                                  <div className={styles.toolBlockLabel}>Output</div>
                                  <pre>{formatJson(tc.result)}</pre>
                                </div>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}

                {/* Typing indicator */}
                {isPlaying && visibleSteps < totalSteps && (
                  <div className={styles.timelineStep}>
                    <div className={styles.timelineGutter}>
                      <div className={`${styles.timelineDot} ${styles.timelineDotPulse}`} />
                    </div>
                    <div className={styles.typingIndicator}>
                      <span /><span /><span />
                    </div>
                  </div>
                )}
              </div>

              {/* Final agent response */}
              {showFinal && trace.final_response && (
                <div className={styles.finalBlock}>
                  <div className={styles.finalHeader}>
                    <div className={styles.finalHeaderLeft}>
                      <div className={`${styles.timelineDot} ${styles.timelineDotSuccess}`} />
                      <span className={styles.finalTitle}>Agent Response</span>
                    </div>
                    <CopyButton text={trace.final_response} />
                  </div>
                  <div className={styles.finalBody}>
                    {renderMarkdown(trace.final_response)}
                  </div>
                </div>
              )}

              {/* Stats row */}
              {showFinal && (
                <div className={styles.traceStats}>
                  <div className={styles.traceStat}>
                    <span className={styles.traceStatVal}>{trace.steps.length}</span>
                    <span className={styles.traceStatKey}>steps</span>
                  </div>
                  <div className={styles.traceStat}>
                    <span className={styles.traceStatVal}>{Object.values(trace.tools_called).reduce((a, b) => a + b, 0)}</span>
                    <span className={styles.traceStatKey}>tool calls</span>
                  </div>
                  <div className={styles.traceStat}>
                    <span className={styles.traceStatVal}>{((trace.total_input_tokens + trace.total_output_tokens) / 1000).toFixed(1)}k</span>
                    <span className={styles.traceStatKey}>tokens</span>
                  </div>
                  <div className={styles.traceStat}>
                    <span className={styles.traceStatVal}>{(trace.total_latency_ms / 1000).toFixed(1)}s</span>
                    <span className={styles.traceStatKey}>latency</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className={styles.emptyTrace}>
              <div className={styles.emptyTraceIcon}>{'>'}_</div>
              <p>Select a simulation above to watch an agent work</p>
            </div>
          )}
        </section>

        {/* Code example */}
        <section className={styles.codeSection}>
          <div className={styles.sectionLabel}>Build your own agent</div>
          <p className={styles.codeSub}>
            Everything above runs on <code>archaitools</code>. Here&apos;s the full agent loop:
          </p>
          <div className={styles.codeWrapper}>
            <div className={styles.codeBar}>
              <span>agent.py</span>
              <CopyButton text={`from archaitools import MarkTools
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

    if response.stop_reason != "tool_use":
        print(response.content[0].text)
        break

    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = mark.execute(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})`} />
            </div>
            <pre className={styles.codeBlock}>
{`from archaitools import MarkTools
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

    if response.stop_reason != "tool_use":
        print(response.content[0].text)
        break

    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = mark.execute(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})`}
            </pre>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
