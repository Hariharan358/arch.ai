'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import styles from './WorkflowVisualizer.module.css'

/* ─── Types ─── */

type NodeType = 'agent' | 'api' | 'backend' | 'event'

interface NodeData {
  id: string
  label: string
  type: NodeType
  description: string
  payload: { sent?: string; returned?: string }
  expandable?: boolean
}

interface SubNode {
  id: string
  label: string
  description: string
  payload: { sent?: string; returned?: string }
}

/* ─── Data ─── */

const nodes: NodeData[] = [
  {
    id: 'agent-query',
    label: 'Agent Query',
    type: 'agent',
    description: 'The AI agent formulates a natural language query for a tool or solution.',
    payload: {
      sent: '{ query: "Find a React auth library with OAuth support" }',
    },
  },
  {
    id: 'mark-estimate',
    label: 'mark_estimate(query)',
    type: 'api',
    description: 'Estimates relevance and price range before committing credits.',
    payload: {
      sent: '{ query: "Find a React auth library..." }',
      returned: '{ relevant: true, price_range: [5, 25], confidence: 0.92 }',
    },
  },
  {
    id: 'mark-buy',
    label: 'mark_buy(query, budget)',
    type: 'api',
    description: 'Submits a purchase request with a credit budget cap.',
    payload: {
      sent: '{ query: "Find a React auth library...", budget: 20 }',
      returned: '[{ solution_id, label, price, rating }, ...]',
    },
    expandable: true,
  },
  {
    id: 'agent-pick',
    label: 'Agent Picks Best',
    type: 'agent',
    description: 'The agent evaluates returned solutions and selects the best match.',
    payload: {
      sent: 'Evaluating 4 candidates by score...',
      returned: '{ selected: "sol_42", label: "AuthKit Pro", price: 12 }',
    },
  },
  {
    id: 'credits-deducted',
    label: 'Credits Deducted',
    type: 'event',
    description: 'Credits are atomically deducted from the agent\'s balance.',
    payload: {
      sent: '{ agent_id: "ag_7x", amount: 12 }',
      returned: '{ prev_balance: 100, new_balance: 88 }',
    },
  },
  {
    id: 'artifact-returned',
    label: 'Artifact Returned',
    type: 'agent',
    description: 'The purchased solution artifact is delivered to the agent.',
    payload: {
      returned: '{ artifact: "auth-kit-pro-v2.1.tgz", docs_url: "...", license: "MIT" }',
    },
  },
  {
    id: 'mark-rate',
    label: 'mark_rate(solution_id, rating)',
    type: 'api',
    description: 'Agent provides feedback to improve future rankings.',
    payload: {
      sent: '{ solution_id: "sol_42", rating: "up" }',
      returned: '{ success: true, new_rating: 4.85 }',
    },
  },
]

const backendSubNodes: SubNode[] = [
  {
    id: 'memo-check',
    label: '1. Memoization Check',
    description: 'Check if this exact query has been resolved recently. Cache hit skips directly to return.',
    payload: {
      sent: '{ cache_key: hash("Find a React auth...") }',
      returned: '{ hit: false, reason: "no matching key" }',
    },
  },
  {
    id: 'privacy-sanitize',
    label: '2. Privacy Sanitization',
    description: 'Strip all PII — emails, names, IP addresses — before processing.',
    payload: {
      sent: '{ raw_query: "Find auth for john@acme.com..." }',
      returned: '{ sanitized: "Find auth for [REDACTED]...", pii_found: 1 }',
    },
  },
  {
    id: 'embedding-search',
    label: '3. Embedding Search',
    description: 'Vector similarity search across the solution database.',
    payload: {
      sent: '{ embedding: float[1536], top_k: 50 }',
      returned: '{ candidates: 47, avg_similarity: 0.82 }',
    },
  },
  {
    id: 'ranking',
    label: '4. Ranking',
    description: 'Score candidates: relevance × rating × (1 / price). Return top results.',
    payload: {
      sent: '{ candidates: 47, weights: { relevance: 0.5, rating: 0.3, price: 0.2 } }',
      returned: '[{ sol_42: 0.94 }, { sol_18: 0.87 }, { sol_7: 0.81 }, ...]',
    },
  },
]

/* ─── Animated Edge ─── */

function FlowEdge({ delay = 0, accent = false }: { delay?: number; accent?: boolean }) {
  return (
    <div className={styles.edgeWrap}>
      <svg width="2" height="36" viewBox="0 0 2 36" className={styles.edgeSvg}>
        <line
          x1="1" y1="0" x2="1" y2="36"
          stroke={accent ? 'var(--accent)' : 'var(--border-hover)'}
          strokeWidth="2"
          strokeDasharray="5 4"
          style={{ animationDelay: `${delay}s` }}
          className={styles.flowLine}
        />
      </svg>
    </div>
  )
}

function SubFlowEdge() {
  return (
    <div className={styles.subEdgeWrap}>
      <svg width="2" height="20" viewBox="0 0 2 20" className={styles.edgeSvg}>
        <line
          x1="1" y1="0" x2="1" y2="20"
          stroke="var(--text-muted)"
          strokeWidth="1.5"
          strokeDasharray="3 3"
          className={styles.flowLine}
        />
      </svg>
    </div>
  )
}

/* ─── Payload Panel ─── */

function PayloadPanel({ node, onClose }: { node: NodeData | SubNode; onClose: () => void }) {
  return (
    <motion.div
      className={styles.payloadOverlay}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className={styles.payloadPanel}
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.payloadHeader}>
          <span className={styles.payloadTitle}>{node.label}</span>
          <button className={styles.payloadClose} onClick={onClose}>
            &times;
          </button>
        </div>
        <p className={styles.payloadDesc}>{node.description}</p>
        {'payload' in node && node.payload.sent && (
          <div className={styles.payloadBlock}>
            <div className={styles.payloadLabel}>
              <span className={styles.arrow}>&#8594;</span> Sent
            </div>
            <pre className={styles.payloadCode}>{node.payload.sent}</pre>
          </div>
        )}
        {'payload' in node && node.payload.returned && (
          <div className={styles.payloadBlock}>
            <div className={`${styles.payloadLabel} ${styles.payloadLabelReturn}`}>
              <span className={styles.arrow}>&#8592;</span> Returned
            </div>
            <pre className={styles.payloadCode}>{node.payload.returned}</pre>
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

/* ─── Credits Counter ─── */

function CreditsCounter({ credits }: { credits: number }) {
  return (
    <div className={styles.creditsWrap}>
      <div className={styles.creditsLabel}>credits</div>
      <motion.div
        className={styles.creditsValue}
        key={credits}
        initial={{ scale: 1.3, color: '#ff4d4d' }}
        animate={{ scale: 1, color: 'var(--accent)' }}
        transition={{ duration: 0.4 }}
      >
        {credits}
      </motion.div>
    </div>
  )
}

/* ─── Main Visualizer ─── */

export default function WorkflowVisualizer() {
  const [expanded, setExpanded] = useState(false)
  const [selectedNode, setSelectedNode] = useState<NodeData | SubNode | null>(null)
  const [credits, setCredits] = useState(100)
  const [purchased, setPurchased] = useState(false)

  const handleNodeClick = useCallback((node: NodeData | SubNode) => {
    setSelectedNode(node)
  }, [])

  const handlePurchase = useCallback(() => {
    if (!purchased) {
      setPurchased(true)
      // Animate credits ticking down
      let current = 100
      const target = 88
      const step = () => {
        current -= 1
        setCredits(current)
        if (current > target) {
          requestAnimationFrame(step)
        }
      }
      requestAnimationFrame(step)
    }
  }, [purchased])

  const resetDemo = useCallback(() => {
    setPurchased(false)
    setCredits(100)
    setExpanded(false)
    setSelectedNode(null)
  }, [])

  const typeClass = (type: NodeType) => {
    switch (type) {
      case 'agent': return styles.nodeAgent
      case 'api': return styles.nodeApi
      case 'backend': return styles.nodeBackend
      case 'event': return styles.nodeEvent
      default: return ''
    }
  }

  const typeLabel = (type: NodeType) => {
    switch (type) {
      case 'agent': return 'agent'
      case 'api': return 'arch.ai api'
      case 'backend': return 'internal'
      case 'event': return 'event'
    }
  }

  return (
    <div className={styles.container}>
      {/* Credits */}
      <CreditsCounter credits={credits} />

      {/* Reset */}
      {purchased && (
        <motion.button
          className={styles.resetBtn}
          onClick={resetDemo}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          reset demo
        </motion.button>
      )}

      {/* Flow */}
      <div className={styles.flow}>
        {nodes.map((node, i) => (
          <div key={node.id}>
            {/* Edge before node (except first) */}
            {i > 0 && <FlowEdge delay={i * 0.15} accent={node.type === 'api'} />}

            {/* Node */}
            <motion.div
              className={`${styles.node} ${typeClass(node.type)}`}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
              onClick={() => {
                if (node.id === 'credits-deducted') handlePurchase()
                handleNodeClick(node)
              }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className={styles.nodeHeader}>
                <span className={styles.nodeLabel}>{node.label}</span>
                <span className={`${styles.nodeType} ${typeClass(node.type)}`}>
                  {typeLabel(node.type)}
                </span>
              </div>
              <div className={styles.nodeDesc}>{node.description}</div>
              {node.expandable && (
                <button
                  className={styles.expandBtn}
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpanded(!expanded)
                  }}
                >
                  {expanded ? '▾ Hide' : '▸ Expand'} arch.ai Backend
                </button>
              )}
              <div className={styles.clickHint}>click to inspect payload</div>
            </motion.div>

            {/* Backend sub-nodes */}
            {node.expandable && (
              <AnimatePresence>
                {expanded && (
                  <motion.div
                    className={styles.subFlow}
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
                  >
                    <div className={styles.subFlowInner}>
                      <div className={styles.backendLabel}>
                        <span className={styles.backendPipe}>│</span> arch.ai Backend Pipeline
                      </div>
                      {backendSubNodes.map((sub, si) => (
                        <div key={sub.id}>
                          {si > 0 && <SubFlowEdge />}
                          <motion.div
                            className={`${styles.node} ${styles.nodeBackend} ${styles.subNode}`}
                            initial={{ opacity: 0, x: -12 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: si * 0.08, duration: 0.3 }}
                            onClick={() => handleNodeClick(sub)}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                          >
                            <div className={styles.nodeHeader}>
                              <span className={styles.nodeLabel}>{sub.label}</span>
                              <span className={`${styles.nodeType} ${styles.nodeBackend}`}>
                                internal
                              </span>
                            </div>
                            <div className={styles.nodeDesc}>{sub.description}</div>
                            <div className={styles.clickHint}>click to inspect</div>
                          </motion.div>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            )}
          </div>
        ))}
      </div>

      {/* Payload panel */}
      <AnimatePresence>
        {selectedNode && (
          <PayloadPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}
      </AnimatePresence>
    </div>
  )
}
