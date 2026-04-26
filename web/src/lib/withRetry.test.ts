import { describe, it, expect, vi } from 'vitest'
import { isRetryableError, withRetry } from './withRetry'

function axiosLike(status?: number) {
  if (status === undefined) return { isAxiosError: true, response: undefined }
  return { isAxiosError: true, response: { status } }
}

describe('isRetryableError', () => {
  it('treats network errors (no response) as retryable', () => {
    expect(isRetryableError(axiosLike())).toBe(true)
  })
  it('retries 408, 429, and 5xx', () => {
    expect(isRetryableError(axiosLike(408))).toBe(true)
    expect(isRetryableError(axiosLike(429))).toBe(true)
    expect(isRetryableError(axiosLike(500))).toBe(true)
    expect(isRetryableError(axiosLike(503))).toBe(true)
    expect(isRetryableError(axiosLike(599))).toBe(true)
  })
  it('does NOT retry 400/401/403/404/422', () => {
    expect(isRetryableError(axiosLike(400))).toBe(false)
    expect(isRetryableError(axiosLike(401))).toBe(false)
    expect(isRetryableError(axiosLike(403))).toBe(false)
    expect(isRetryableError(axiosLike(404))).toBe(false)
    expect(isRetryableError(axiosLike(422))).toBe(false)
  })
  it('non-error inputs are not retryable', () => {
    expect(isRetryableError(undefined)).toBe(false)
    expect(isRetryableError(null)).toBe(false)
  })
})

describe('withRetry', () => {
  it('returns the value on first try', async () => {
    const fn = vi.fn().mockResolvedValue(42)
    const out = await withRetry(fn)
    expect(out).toBe(42)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('retries transient errors and then succeeds', async () => {
    const fn = vi.fn()
      .mockRejectedValueOnce(axiosLike(503))
      .mockRejectedValueOnce(axiosLike())
      .mockResolvedValue('ok')
    const out = await withRetry(fn, { attempts: 3, baseDelayMs: 1, maxDelayMs: 5 })
    expect(out).toBe('ok')
    expect(fn).toHaveBeenCalledTimes(3)
  })

  it('does not retry permanent failures', async () => {
    const fn = vi.fn().mockRejectedValue(axiosLike(401))
    await expect(withRetry(fn, { attempts: 5, baseDelayMs: 1 })).rejects.toBeDefined()
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('throws after exhausting attempts', async () => {
    const fn = vi.fn().mockRejectedValue(axiosLike(503))
    await expect(withRetry(fn, { attempts: 3, baseDelayMs: 1, maxDelayMs: 5 })).rejects.toBeDefined()
    expect(fn).toHaveBeenCalledTimes(3)
  })

  it('invokes onRetry with attempt + delay', async () => {
    const onRetry = vi.fn()
    const fn = vi.fn()
      .mockRejectedValueOnce(axiosLike(503))
      .mockResolvedValue('ok')
    await withRetry(fn, { attempts: 3, baseDelayMs: 1, maxDelayMs: 5, onRetry })
    expect(onRetry).toHaveBeenCalledTimes(1)
    const arg = onRetry.mock.calls[0][0]
    expect(arg.attempt).toBe(1)
    expect(typeof arg.delayMs).toBe('number')
    expect(arg.delayMs).toBeGreaterThan(0)
  })
})
