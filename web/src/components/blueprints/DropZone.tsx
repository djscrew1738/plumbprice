'use client'

import { useState, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Upload, Layers, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MAX_BLUEPRINT_SIZE_MB } from '@/lib/constants'

interface DropZoneProps {
  onFiles: (files: File[]) => void
  isUploading: boolean
}

export function DropZone({ onFiles, isUploading }: DropZoneProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      if (isUploading) return
      const files = Array.from(e.dataTransfer.files).filter(
        f => f.type === 'application/pdf' || f.type.startsWith('image/')
      )
      if (files.length) onFiles(files)
    },
    [onFiles, isUploading]
  )

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (files.length) onFiles(files)
    e.target.value = ''
  }

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      inputRef.current?.click()
    }
  }, [])

  return (
    <motion.div
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      animate={{ scale: dragging ? 1.01 : 1 }}
      transition={{ duration: 0.15 }}
      onClick={() => !isUploading && inputRef.current?.click()}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label="Upload blueprint files. Press Enter or Space to open file picker"
      className={cn(
        'relative cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center outline-none transition-all focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
        isUploading && 'pointer-events-none opacity-60'
      )}
      style={{
        borderColor: dragging ? 'hsl(221 83% 55% / 0.6)' : 'rgba(255,255,255,0.10)',
        background: dragging
          ? 'linear-gradient(135deg, hsl(221 83% 55% / 0.07), hsl(230 76% 52% / 0.04))'
          : 'rgba(255,255,255,0.015)',
        boxShadow: dragging
          ? 'inset 0 0 0 1px hsl(221 83% 55% / 0.15), 0 8px 32px hsl(221 83% 55% / 0.08)'
          : 'none',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,image/*"
        multiple
        className="hidden"
        onChange={handleChange}
        disabled={isUploading}
      />

      {dragging && (
        <div
          className="pointer-events-none absolute inset-0 rounded-2xl"
          style={{
            background: 'radial-gradient(ellipse at 50% 50%, hsl(221 83% 55% / 0.08), transparent 70%)',
          }}
          aria-hidden="true"
        />
      )}

      <div
        className="relative mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl transition-all"
        style={{
          background: dragging
            ? 'linear-gradient(135deg, hsl(221 83% 55% / 0.2), hsl(230 76% 52% / 0.15))'
            : 'rgba(255,255,255,0.04)',
          border: dragging
            ? '1px solid hsl(221 83% 55% / 0.4)'
            : '1px solid rgba(255,255,255,0.08)',
          boxShadow: dragging ? '0 0 20px hsl(221 83% 55% / 0.15)' : 'none',
        }}
      >
        {isUploading
          ? <Loader2 size={26} className="animate-spin text-blue-400" />
          : dragging
            ? <Upload size={26} className="text-blue-400" />
            : <Layers size={26} className="text-zinc-500" />
        }
      </div>

      <p className="mb-1 text-sm font-bold text-zinc-300">
        {isUploading ? 'Uploading…' : dragging ? 'Drop your files here' : 'Upload blueprint files'}
      </p>
      <p className="text-xs text-zinc-600">
        Drag & drop or{' '}
        <span className="font-bold" style={{ color: 'hsl(221 83% 65%)' }}>browse files</span>
        {' '}· PDF or image · max {MAX_BLUEPRINT_SIZE_MB} MB
      </p>
    </motion.div>
  )
}
