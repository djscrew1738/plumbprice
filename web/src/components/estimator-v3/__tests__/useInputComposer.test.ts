import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useInputComposer } from '../hooks/useInputComposer'

const mockQuickAnalyze = vi.fn()

vi.mock('@/lib/api-v3', () => ({
  blueprintApiV3: {
    quickAnalyze: (...args: unknown[]) => mockQuickAnalyze(...args),
  },
}))

vi.mock('@/lib/speech', () => ({
  useSpeechRecognition: () => ({
    supported: true,
    listening: false,
    transcript: '',
    start: vi.fn(),
    stop: vi.fn(),
    reset: vi.fn(),
  }),
}))

describe('useInputComposer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockQuickAnalyze.mockResolvedValue({ data: { summary: 'Detected 3 toilets' } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('has correct initial state', () => {
    const { result } = renderHook(() => useInputComposer())
    expect(result.current.input).toBe('')
    expect(result.current.attachedImage).toBeNull()
    expect(result.current.imagePreview).toBeNull()
    expect(result.current.imageAnalyzing).toBe(false)
    expect(result.current.blueprintSummary).toBeNull()
    expect(result.current.compareMode).toBe(false)
    expect(result.current.voiceReadBack).toBe(false)
  })

  it('setInput updates input text', () => {
    const { result } = renderHook(() => useInputComposer())
    act(() => result.current.setInput('Hello'))
    expect(result.current.input).toBe('Hello')
  })

  it('composeMessage returns input when no blueprint', () => {
    const { result } = renderHook(() => useInputComposer())
    act(() => result.current.setInput('Test job'))
    expect(result.current.composeMessage()).toBe('Test job')
  })

  it('composeMessage combines blueprint and input', async () => {
    const { result } = renderHook(() => useInputComposer())
    const file = new File([''], 'test.jpg', { type: 'image/jpeg' })

    await act(async () => {
      await result.current.handleFileSelect(file)
    })

    act(() => result.current.setInput('Add details'))
    expect(result.current.composeMessage()).toBe('Detected 3 toilets\n\nAdd details')
  })

  it('clear resets all input state', () => {
    const { result } = renderHook(() => useInputComposer())
    act(() => {
      result.current.setInput('Test')
      result.current.blueprintSummary = 'Summary'
      result.current.imagePreview = 'blob:mock'
    })

    act(() => result.current.clear())

    expect(result.current.input).toBe('')
    expect(result.current.blueprintSummary).toBeNull()
    expect(result.current.imagePreview).toBeNull()
    expect(result.current.attachedImage).toBeNull()
  })

  it('toggleCompareMode toggles state', () => {
    const { result } = renderHook(() => useInputComposer())
    expect(result.current.compareMode).toBe(false)
    act(() => result.current.toggleCompareMode())
    expect(result.current.compareMode).toBe(true)
    act(() => result.current.toggleCompareMode())
    expect(result.current.compareMode).toBe(false)
  })

  it('toggleVoiceReadBack toggles and persists to localStorage', () => {
    const { result } = renderHook(() => useInputComposer())
    expect(result.current.voiceReadBack).toBe(false)
    act(() => result.current.toggleVoiceReadBack())
    expect(result.current.voiceReadBack).toBe(true)
    expect(localStorage.getItem('v3_voice_readback')).toBe('true')
    act(() => result.current.toggleVoiceReadBack())
    expect(result.current.voiceReadBack).toBe(false)
    expect(localStorage.getItem('v3_voice_readback')).toBe('false')
  })

  it('handleSubmit calls onSend with composed message', () => {
    const onSend = vi.fn()
    const { result } = renderHook(() => useInputComposer({ onSend }))

    act(() => result.current.setInput('Test message'))
    act(() => result.current.handleSubmit())

    expect(onSend).toHaveBeenCalledWith('Test message', { compareMode: false })
    expect(result.current.input).toBe('')
  })

  it('handleSubmit does nothing with empty message', () => {
    const onSend = vi.fn()
    const { result } = renderHook(() => useInputComposer({ onSend }))

    act(() => result.current.handleSubmit())
    expect(onSend).not.toHaveBeenCalled()
  })

  it('handleKeyDown submits on Enter without shift', () => {
    const onSend = vi.fn()
    const { result } = renderHook(() => useInputComposer({ onSend }))

    act(() => result.current.setInput('Test'))
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false }) as unknown as React.KeyboardEvent<HTMLTextAreaElement>
    Object.defineProperty(event, 'preventDefault', { value: vi.fn() })

    act(() => result.current.handleKeyDown(event))

    expect(event.preventDefault).toHaveBeenCalled()
    expect(onSend).toHaveBeenCalled()
  })

  it('handleKeyDown does not submit on Shift+Enter', () => {
    const onSend = vi.fn()
    const { result } = renderHook(() => useInputComposer({ onSend }))

    act(() => result.current.setInput('Test'))
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true }) as unknown as React.KeyboardEvent<HTMLTextAreaElement>
    Object.defineProperty(event, 'preventDefault', { value: vi.fn() })

    act(() => result.current.handleKeyDown(event))

    expect(event.preventDefault).not.toHaveBeenCalled()
    expect(onSend).not.toHaveBeenCalled()
  })

  it('handleFileSelect analyzes image and sets summary', async () => {
    const { result } = renderHook(() => useInputComposer())
    const file = new File([''], 'test.jpg', { type: 'image/jpeg' })

    await act(async () => {
      await result.current.handleFileSelect(file)
    })

    expect(mockQuickAnalyze).toHaveBeenCalledWith(file)
    expect(result.current.blueprintSummary).toBe('Detected 3 toilets')
    expect(result.current.imageAnalyzing).toBe(false)
  })

  it('handleFileSelect rejects non-image files', async () => {
    const { result } = renderHook(() => useInputComposer())
    const file = new File([''], 'test.pdf', { type: 'application/pdf' })

    await act(async () => {
      await result.current.handleFileSelect(file)
    })

    expect(mockQuickAnalyze).not.toHaveBeenCalled()
  })

  it('handleFileSelect rejects oversized files', async () => {
    const { result } = renderHook(() => useInputComposer())
    const file = new File(['x'], 'test.jpg', { type: 'image/jpeg' })
    Object.defineProperty(file, 'size', { value: 101 * 1024 * 1024 })

    await act(async () => {
      await result.current.handleFileSelect(file)
    })

    expect(mockQuickAnalyze).not.toHaveBeenCalled()
    expect(result.current.blueprintSummary).toBe('Image too large — max 100 MB.')
  })

  it('handleRemoveImage clears image state', async () => {
    const { result } = renderHook(() => useInputComposer())
    const file = new File([''], 'test.jpg', { type: 'image/jpeg' })

    await act(async () => {
      await result.current.handleFileSelect(file)
    })

    expect(result.current.imagePreview).not.toBeNull()
    expect(result.current.blueprintSummary).not.toBeNull()

    act(() => result.current.handleRemoveImage())

    expect(result.current.imagePreview).toBeNull()
    expect(result.current.attachedImage).toBeNull()
    expect(result.current.blueprintSummary).toBeNull()
  })
})
