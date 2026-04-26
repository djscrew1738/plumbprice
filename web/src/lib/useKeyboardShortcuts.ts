'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

const SHORTCUT_HELP = [
  { keys: '⌘K / Ctrl+K', description: 'Open command palette' },
  { keys: 'N', description: 'New estimate' },
  { keys: 'G H', description: 'Go to Home' },
  { keys: 'G E', description: 'Go to Estimates' },
  { keys: 'G P', description: 'Go to Pipeline' },
  { keys: '?', description: 'Show this help' },
  { keys: 'Esc', description: 'Close dialogs' },
]

export { SHORTCUT_HELP }

export function useKeyboardShortcuts() {
  const router = useRouter()

  useEffect(() => {
    let sequence = ''
    let sequenceTimer: ReturnType<typeof setTimeout> | null = null

    function resetSequence() {
      sequence = ''
    }

    function handleKeyDown(event: KeyboardEvent) {
      // Cmd/Ctrl+K opens the command palette regardless of focus context.
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        window.dispatchEvent(new CustomEvent('show-command-palette'))
        return
      }

      // Ignore when typing in an input/textarea/select
      const tag = (event.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return
      if ((event.target as HTMLElement)?.isContentEditable) return
      if (event.metaKey || event.ctrlKey || event.altKey) return

      const key = event.key.toUpperCase()

      // Single-key shortcuts
      if (key === 'N') {
        event.preventDefault()
        router.push('/estimator')
        return
      }

      // Two-key "G ?" sequences
      if (sequence === 'G') {
        if (sequenceTimer) clearTimeout(sequenceTimer)
        switch (key) {
          case 'H': router.push('/'); break
          case 'E': router.push('/estimates'); break
          case 'P': router.push('/pipeline'); break
          case 'R': router.push('/proposals'); break
          case 'A': router.push('/admin'); break
        }
        resetSequence()
        return
      }

      if (key === 'G') {
        sequence = 'G'
        sequenceTimer = setTimeout(resetSequence, 1500)
        return
      }

      // ? key — dispatch custom event to show shortcuts dialog
      if (event.key === '?') {
        event.preventDefault()
        window.dispatchEvent(new CustomEvent('show-shortcuts'))
        return
      }

      resetSequence()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      if (sequenceTimer) clearTimeout(sequenceTimer)
    }
  }, [router])
}
