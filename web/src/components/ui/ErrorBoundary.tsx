'use client'

import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from './Button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  override state = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleRetry = () => {
    // Reset boundary state so children re-render without losing app state.
    // If the same error reoccurs immediately, the user can use Reload Page.
    this.setState({ hasError: false, error: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  override render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center px-4 text-center">
          <div className="mb-4 flex size-16 items-center justify-center rounded-full bg-red-500/10">
            <AlertCircle size={32} className="text-red-500" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-[color:var(--ink)]">
            Something went wrong
          </h2>
          <p className="mb-4 max-w-md text-sm text-[color:var(--muted-ink)]">
            We encountered an error while loading this page. Don&apos;t worry, this happens sometimes.
          </p>
          <div className="flex gap-2">
            <Button onClick={this.handleRetry} variant="secondary">
              <RefreshCw size={16} className="mr-2" />
              Try Again
            </Button>
            <Button onClick={this.handleReload} variant="ghost">
              Reload Page
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export function ErrorFallback({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 flex size-16 items-center justify-center rounded-full bg-red-500/10">
        <AlertCircle size={32} className="text-red-500" />
      </div>
      <h2 className="mb-2 text-xl font-semibold text-[color:var(--ink)]">Oops!</h2>
      <p className="mb-4 max-w-md text-sm text-[color:var(--muted-ink)]">{message}</p>
      <Button onClick={onRetry} variant="secondary">
        <RefreshCw size={16} className="mr-2" />
        Try Again
      </Button>
    </div>
  )
}
