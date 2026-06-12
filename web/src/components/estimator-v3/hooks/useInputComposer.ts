'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { blueprintApiV3 } from '@/lib/api-v3'
import { useSpeechRecognition } from '@/lib/speech'

export interface UseInputComposerOptions {
  onSend?: (message: string, options: { compareMode: boolean }) => void
}

export function useInputComposer({ onSend }: UseInputComposerOptions = {}) {
  const [input, setInput] = useState('')
  const [attachedImage, setAttachedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageAnalyzing, setImageAnalyzing] = useState(false)
  const [blueprintSummary, setBlueprintSummary] = useState<string | null>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [voiceReadBack, setVoiceReadBack] = useState(() => {
    try { return localStorage.getItem('v3_voice_readback') === 'true' } catch { return false }
  })

  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)

  const speech = useSpeechRecognition({ silenceTimeoutMs: 2000 })

  // Apply speech transcript to input
  useEffect(() => {
    if (speech.transcript) {
      setInput(speech.transcript)
    }
  }, [speech.transcript])

  const composeMessage = useCallback(() => {
    const messageParts = [blueprintSummary, input].filter(Boolean)
    if (messageParts.length > 1) {
      return `${messageParts[0]}\n\n${messageParts[1]}`
    }
    return input || blueprintSummary || ''
  }, [blueprintSummary, input])

  const clear = useCallback(() => {
    setInput('')
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview)
    }
    setAttachedImage(null)
    setImagePreview(null)
    setBlueprintSummary(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [imagePreview])

  const compressImage = useCallback(async (file: File, maxWidth = 1920, maxHeight = 1920, quality = 0.85): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        let { width, height } = img
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height)
          width *= ratio
          height *= ratio
        }
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) { reject(new Error('Canvas context not available')); return }
        ctx.drawImage(img, 0, 0, width, height)
        canvas.toBlob((blob) => {
          if (blob) resolve(blob)
          else reject(new Error('Canvas toBlob failed'))
        }, file.type, quality)
      }
      img.onerror = reject
      img.src = URL.createObjectURL(file)
    })
  }, [])

  const handleFileSelect = useCallback(async (file: File | undefined) => {
    if (!file) return
    if (!file.type.startsWith('image/')) return
    const maxBytes = 100 * 1024 * 1024 // 100 MB
    if (file.size > maxBytes) {
      setBlueprintSummary('Image too large — max 100 MB.')
      return
    }

    // Compress images > 2MB before upload
    let processedFile = file
    if (file.size > 2 * 1024 * 1024) {
      try {
        const compressed = await compressImage(file)
        processedFile = new File([compressed], file.name, { type: file.type })
      } catch {
        // Fall back to original file
      }
    }

    setAttachedImage(processedFile)
    setImagePreview(URL.createObjectURL(processedFile))
    setImageAnalyzing(true)
    try {
      const { data } = await blueprintApiV3.quickAnalyze(processedFile)
      setBlueprintSummary(data.summary)
    } catch {
      setBlueprintSummary('Blueprint analysis failed — you can still describe the job.')
    } finally {
      setImageAnalyzing(false)
    }
  }, [compressImage])

  const handleRemoveImage = useCallback(() => {
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview)
    }
    setAttachedImage(null)
    setImagePreview(null)
    setBlueprintSummary(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [imagePreview])

  const toggleCompareMode = useCallback(() => {
    setCompareMode(v => !v)
  }, [])

  const toggleVoiceReadBack = useCallback(() => {
    setVoiceReadBack((prev: boolean) => {
      const next = !prev
      try { localStorage.setItem('v3_voice_readback', String(next)) } catch { /* noop */ }
      return next
    })
  }, [])

  const focusInput = useCallback(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = useCallback(() => {
    const message = composeMessage()
    if (!message.trim()) return
    onSend?.(message, { compareMode })
    clear()
  }, [composeMessage, compareMode, onSend, clear])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>, options?: { onEditLast?: () => void }) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
      return
    }
    if (e.key === 'ArrowUp' && !input.trim() && options?.onEditLast) {
      e.preventDefault()
      options.onEditLast()
    }
  }, [handleSubmit, input])

  return {
    // State
    input,
    setInput,
    attachedImage,
    imagePreview,
    imageAnalyzing,
    blueprintSummary,
    compareMode,
    voiceReadBack,
    speech,

    // Refs
    fileInputRef,
    inputRef,

    // Actions
    composeMessage,
    clear,
    handleFileSelect,
    handleRemoveImage,
    toggleCompareMode,
    toggleVoiceReadBack,
    focusInput,
    handleSubmit,
    handleKeyDown,
  }
}
