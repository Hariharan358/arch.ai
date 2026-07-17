import type { Metadata } from 'next'
import { JetBrains_Mono, Sora } from 'next/font/google'
import './globals.css'
import Background from '@/components/Background'

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['300', '400', '500', '600', '700'],
})

const sora = Sora({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['300', '400', '500', '600', '700'],
})

export const metadata: Metadata = {
  title: 'arch.ai — The Agent Marketplace',
  description: 'The marketplace your agents already know how to use.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${jetbrainsMono.variable} ${sora.variable}`}>
        <Background />
        {children}
      </body>
    </html>
  )
}
