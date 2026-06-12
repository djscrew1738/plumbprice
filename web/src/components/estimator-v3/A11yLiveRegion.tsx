'use client'

import { useEffect, useRef } from 'react'

interface A11yLiveRegionProps {
  streamingText?: string
  isStreaming?: boolean
  lastEvent?: string
}

/**
 * aria-live region for streaming chat announcements.
 * Announces when the AI starts responding and when estimate data arrives.
 */
export function A11yLiveRegion({ streamingText, isStreaming, lastEvent }: A11yLiveRegionProps) {
  const announcedRef = useRef<string>('')

  useEffect(() => {
    if (isStreaming && streamingText && streamingText !== announcedRef.current) {
      // Debounce announcements to avoid rapid-fire screen reader chatter
      const timeout = setTimeout(() => {
        announcedRef.current = streamingText
      }, 1500)
      return () => clearTimeout(timeout)
    }
  }, [isStreaming, streamingText])

  return (
    <div className="sr-only" aria-live="polite" aria-atomic="false">
      {isStreaming && lastEvent === 'pricing' && 'Estimate generated. Viewing breakdown.'}
      {isStreaming && lastEvent === 'clarification' && 'Clarification needed. Please answer the question.'}
      {isStreaming && lastEvent === 'error' && 'An error occurred. Please try again.'}
    </div>
  )
}
