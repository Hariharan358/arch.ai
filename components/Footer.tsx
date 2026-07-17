import styles from './Footer.module.css'

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerLeft}>© 2026 arch.ai — Agent marketplace infrastructure</div>
      <div className={styles.footerLinks}>
        <a href="#">Docs</a>
        <a href="#">GitHub</a>
        <a href="#">Status</a>
        <a href="#">Discord</a>
      </div>
    </footer>
  )
}
