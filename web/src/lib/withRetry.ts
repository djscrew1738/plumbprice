/**
 * Generic retry helper for transient HTTP failures on flaky networks
 * (LTE handoffs, captive portals, hotspot drops). Complements
 * `outbox.ts`, which queues mutations while *offline*; this is for when
 * the user is online-ish and a request just happened to bonk.
 *
 * Strategy
 * --------
 * - Wrap any async function that returns a Promise.
 * - Retry on:
 *   * AxiosError with no `response` (network / DNS / abort)
 *   * 408 Request Timeout
 *   * 429 Too Many Requests
 *   * 5xx Server Error
 * - Back off exponentially with a small jitter (avoids thundering herd
 *   when LTE comes back up and 5 mutations all retry at once).
 * - Default: 3 attempts (i.e. 1 try + 2 retries). Total worst-case wall
 *   time ~3.5s with defaults — short enough that a user tap still feels
 *   responsive when it succeeds on attempt 2.
 * - 4xx responses (other than 408/429) are NOT retried — those are the
 *   user's fault (validation, auth) and retrying just hides bugs.
 */

import type { AxiosError } from 'axios'

export interface RetryOptions {
  /** Total attempts including the first. Default 3. */
  attempts?: number
  /** Base delay in ms; doubles each attempt. Default 250. */
  baseDelayMs?: number
  /** Cap on per-attempt delay. Default 4000. */
  maxDelayMs?: number
  /** Optional callback for telemetry / Sentry breadcrumbs. */
  onRetry?: (info: { attempt: number; error: unknown; delayMs: number }) => void
}

const DEFAULTS: Required<Omit<RetryOptions, 'onRetry'>> = {
  attempts: 3,
  baseDelayMs: 250,
  maxDelayMs: 4000,
}

export function isRetryableError(err: unknown): boolean {
  const e = err as AxiosError | undefined
  if (!e || typeof e !== 'object') return false
  // Network failure (no response object)
  if (!e.response) {
    // axios sets `code` for network/DNS/abort. Anything without a
    // response is a transient candidate.
    return true
  }
  const status = e.response.status
  if (status === 408 || status === 429) return true
  if (status >= 500 && status <= 599) return true
  return false
}

function computeDelay(attempt: number, base: number, cap: number): number {
  const exponential = base * Math.pow(2, attempt - 1)
  const jitter = Math.random() * base
  return Math.min(cap, exponential + jitter)
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {},
): Promise<T> {
  const { attempts, baseDelayMs, maxDelayMs } = { ...DEFAULTS, ...options }
  let lastErr: unknown
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await fn()
    } catch (err) {
      lastErr = err
      if (attempt >= attempts || !isRetryableError(err)) {
        throw err
      }
      const delayMs = computeDelay(attempt, baseDelayMs, maxDelayMs)
      options.onRetry?.({ attempt, error: err, delayMs })
      await new Promise((resolve) => setTimeout(resolve, delayMs))
    }
  }
  // Unreachable, but TypeScript wants it.
  throw lastErr
}
