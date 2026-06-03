'use client'

import ReactMarkdown from 'react-markdown'
import type { ComponentProps } from 'react'
import type { ExtraProps } from 'react-markdown'

type AnchorProps = ComponentProps<'a'> & ExtraProps

function SafeLink(props: AnchorProps) {
  const { href, children, node: _node, ...rest } = props
  void _node // excluded from spread to avoid invalid DOM attribute
  const external = typeof href === 'string' && /^https?:\/\//i.test(href)
  return (
    <a
      href={href}
      {...rest}
      {...(external ? { target: '_blank', rel: 'noopener noreferrer nofollow' } : {})}
    >
      {children}
    </a>
  )
}

interface SafeMarkdownProps {
  children: string
}

/**
 * Hardened markdown renderer for untrusted LLM output.
 *
 * Security posture:
 * - react-markdown v9 strips raw HTML by default (no <script>, <iframe>, etc.)
 * - The default urlTransform strips dangerous protocols (javascript:, data:, etc.)
 * - SafeLink adds rel="noopener noreferrer nofollow" to external links
 */
export function SafeMarkdown({ children }: SafeMarkdownProps) {
  return (
    <ReactMarkdown components={{ a: SafeLink }}>
      {children}
    </ReactMarkdown>
  )
}
