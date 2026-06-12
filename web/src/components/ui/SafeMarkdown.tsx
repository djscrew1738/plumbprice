'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ComponentProps } from 'react'
import type { ExtraProps } from 'react-markdown'
import { Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

type AnchorProps = ComponentProps<'a'> & ExtraProps

type CodeProps = ComponentProps<'code'> & ExtraProps

type DetailsProps = ComponentProps<'details'> & ExtraProps

type SummaryProps = ComponentProps<'summary'> & ExtraProps

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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-md border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-1 text-xs text-[color:var(--ink)] opacity-60 transition-opacity hover:opacity-100"
      aria-label="Copy code"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function CodeBlock(props: CodeProps) {
  const { children, className, node: _node, ...rest } = props
  void _node
  const isBlock = typeof className === 'string' && className.startsWith('language-')
  const codeText = typeof children === 'string' ? children : ''
  if (!isBlock) {
    return (
      <code className={cn('rounded bg-[color:var(--panel-strong)] px-1 py-0.5 text-sm', className)} {...rest}>
        {children}
      </code>
    )
  }
  return (
    <div className="relative my-3 overflow-hidden rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)]">
      <CopyButton text={codeText} />
      <pre className="overflow-x-auto p-4 text-sm leading-relaxed text-[color:var(--ink)]">
        <code className={className} {...rest}>
          {children}
        </code>
      </pre>
    </div>
  )
}

function DetailsBlock(props: DetailsProps) {
  const { children, node: _node, ...rest } = props
  void _node
  return (
    <details className="my-3 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)]" {...rest}>
      {children}
    </details>
  )
}

function SummaryBlock(props: SummaryProps) {
  const { children, node: _node, ...rest } = props
  void _node
  return (
    <summary className="cursor-pointer select-none px-4 py-2 text-sm font-medium text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)]" {...rest}>
      {children}
    </summary>
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
    <ReactMarkdown
      components={{
        a: SafeLink,
        code: CodeBlock,
        details: DetailsBlock,
        summary: SummaryBlock,
        table: (props) => (
          <div className="my-3 overflow-x-auto rounded-lg border border-[color:var(--line)]">
            <table className="w-full text-left text-sm text-[color:var(--ink)]">{props.children}</table>
          </div>
        ),
        thead: (props) => <thead className="bg-[color:var(--panel-strong)] text-xs font-semibold uppercase">{props.children}</thead>,
        tbody: (props) => <tbody className="divide-y divide-[color:var(--line)]">{props.children}</tbody>,
        tr: (props) => <tr className="hover:bg-[color:var(--panel-strong)]/50">{props.children}</tr>,
        th: (props) => <th className="px-4 py-2">{props.children}</th>,
        td: (props) => <td className="px-4 py-2">{props.children}</td>,
      }}
    >
      {children}
    </ReactMarkdown>
  )
}
