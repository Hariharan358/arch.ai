'use client'

import { useState, useEffect, useRef } from 'react'
import styles from './Nav.module.css'
import UserInfo from './auth/UserInfo'
import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

export default function Nav() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [balance, setBalance] = useState<number | null>(null)
  const [walletOpen, setWalletOpen] = useState(false)
  const walletRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchBalance = () => {
      fetch(`${API_BASE}/api/commerce/balance?user_id=default_user`)
        .then((r) => r.json())
        .then((d) => setBalance(d.balance ?? null))
        .catch(() => {})
    }
    fetchBalance()
    const interval = setInterval(fetchBalance, 15000)
    window.addEventListener('wallet-refresh', fetchBalance)
    return () => {
      clearInterval(interval)
      window.removeEventListener('wallet-refresh', fetchBalance)
    }
  }, [])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (walletRef.current && !walletRef.current.contains(e.target as Node)) {
        setWalletOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <nav className={styles.nav}>
      <Link href="/" className={styles.navLogo}>
        arch<span>.</span>ai
      </Link>
      <div className={styles.navLinks}>
        <Link href="/marketplace">Marketplace</Link>
        <Link href="/sdk">SDK</Link>
        <Link href="/docs">Docs</Link>
        <Link href="/dashboard">Dashboard</Link>
        <Link href="/workflow">Visualization</Link>

        <div className={styles.walletWrap} ref={walletRef}>
          <button
            className={styles.walletBtn}
            onClick={() => setWalletOpen(!walletOpen)}
            aria-label="Wallet"
          >
            <span className={styles.walletIcon}>◈</span>
            <span className={styles.walletBalance}>
              {balance !== null ? balance.toLocaleString() : '—'}
            </span>
          </button>

          {walletOpen && (
            <div className={styles.walletDropdown}>
              <div className={styles.walletHeader}>Token Wallet</div>
              <div className={styles.walletAmount}>
                <span className={styles.walletAmountIcon}>◈</span>
                <span className={styles.walletAmountValue}>
                  {balance !== null ? balance.toLocaleString() : '—'}
                </span>
                <span className={styles.walletAmountLabel}>tokens</span>
              </div>
              <div className={styles.walletActions}>
                <Link
                  href="/dashboard"
                  className={styles.walletAction}
                  onClick={() => setWalletOpen(false)}
                >
                  View Dashboard
                </Link>
                <Link
                  href="/marketplace"
                  className={styles.walletAction}
                  onClick={() => setWalletOpen(false)}
                >
                  Browse Marketplace
                </Link>
              </div>
            </div>
          )}
        </div>

        <UserInfo onAuthChange={setLoggedIn} />
        {!loggedIn && (
          <Link href="/auth/signup" className={styles.navCta}>
            Get Started
          </Link>
        )}
      </div>
    </nav>
  )
}
