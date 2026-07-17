'use client'

import styles from './Hero.module.css'
import Link from 'next/link'
import { useState, useEffect, useCallback } from 'react'

const ROTATING_WORDS = ['tradable.', 'reusable.', 'accessible.']

export default function Hero() {
  const [copied, setCopied] = useState(false)
  const [wordIndex, setWordIndex] = useState(0)
  const [displayed, setDisplayed] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText('pip install archaitools')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const tick = useCallback(() => {
    const currentWord = ROTATING_WORDS[wordIndex]
    if (!isDeleting) {
      setDisplayed(currentWord.slice(0, displayed.length + 1))
      if (displayed.length + 1 === currentWord.length) {
        setTimeout(() => setIsDeleting(true), 1500)
      }
    } else {
      setDisplayed(currentWord.slice(0, displayed.length - 1))
      if (displayed.length === 0) {
        setIsDeleting(false)
        setWordIndex((prev) => (prev + 1) % ROTATING_WORDS.length)
      }
    }
  }, [wordIndex, displayed, isDeleting])

  useEffect(() => {
    const timer = setTimeout(tick, isDeleting ? 75 : 150)
    return () => clearTimeout(timer)
  }, [displayed, isDeleting, tick])

  return (
    <section className={styles.hero}>
      <div className={styles.heroGlow}></div>
      <h1 className={styles.heroTitle}>
        Making AI agent reasoning
        <br />
        <em>{displayed}</em>
        <span className={styles.cursor}>|</span>
      </h1>
      <a href="https://pypi.org/project/archaitools/" target="_blank" rel="noopener noreferrer" className={styles.installBar} style={{ textDecoration: 'none' }}>
        <div className={styles.installLabel}>Get ArchaiTools <span className={styles.installChevron}></span></div>
        <div className={styles.installCommand}>
          <code><span className={styles.installCmd}>pip</span> <span className={styles.installFlag}>install</span> <span className={styles.installPkg}>archaitools</span></code>
          <button className={styles.installCopy} onClick={handleCopy} aria-label="Copy command">
            {copied ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
            )}
          </button>
        </div>
      </a>
      <div className={styles.heroActions}>
        <Link href="/auth/signup" className={styles.btnPrimary} style={{ textDecoration: 'none' }}>Create Account</Link>
        <Link href="/marketplace" className={styles.btnSecondary} style={{ textDecoration: 'none' }}>Browse Marketplace →</Link>
        <a href="#marketplace" className={styles.btnSecondary} style={{ textDecoration: 'none' }}>Search Workflows ↓</a>
      </div>
      <div className={styles.heroCode}>
        <pre>
          <span className={styles.cmt}># pip install archaitools</span>
          {'\n'}
          <span className={styles.kw}>from</span> archaitools <span className={styles.kw}>import</span>{' '}
          <span className={styles.fn}>MarkTools</span>
          {'\n\n'}
          <span className={styles.cmt}># Drop into any agent framework</span>
          {'\n'}
          tools <span className={styles.kw}>=</span>{' '}
          <span className={styles.fn}>MarkTools</span>(api_key=<span className={styles.str}>&quot;mk_...&quot;</span>)
          {'\n\n'}
          <span className={styles.cmt}># Claude</span>
          {'\n'}
          response <span className={styles.kw}>=</span> client.messages.create({'\n'}
          {'  '}tools<span className={styles.kw}>=</span>tools.<span className={styles.fn}>to_anthropic</span>(),{'\n'}
          {'  '}messages<span className={styles.kw}>=</span>[...]{'\n'}
          )
          {'\n\n'}
          <span className={styles.cmt}># Execute tool calls automatically</span>
          {'\n'}
          result <span className={styles.kw}>=</span> tools.<span className={styles.fn}>execute</span>(
          block.name, block.input)
        </pre>
      </div>
    </section>
  )
}
