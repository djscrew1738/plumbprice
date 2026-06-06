'use client'

/**
 * PhotoAnnotationCanvas
 *
 * Renders a photo with bounding-box overlays for detected fixtures.
 * Each box is drawn on a transparent <canvas> layered over the <img>.
 * Boxes flagged `needs_review` are highlighted in amber; confirmed
 * detections are shown in green.
 *
 * Usage:
 *   <PhotoAnnotationCanvas
 *     src="/api/v1/blueprints/pages/42/image"
 *     detections={detections}
 *     onSelect={(det) => setSelectedDetection(det)}
 *   />
 */

import { useEffect, useRef, useState } from 'react'

export interface Detection {
  id: number
  fixture_type: string
  confidence: number
  needs_review: boolean
  /** Bounding box in normalised [0, 1] coordinates */
  bbox?: { x: number; y: number; w: number; h: number }
}

interface PhotoAnnotationCanvasProps {
  src: string
  detections: Detection[]
  /** Called when the user clicks a bounding box */
  onSelect?: (detection: Detection) => void
  className?: string
}

const CONFIRMED_COLOR = 'rgba(34, 197, 94, 0.85)'   // green-500
const REVIEW_COLOR = 'rgba(245, 158, 11, 0.85)'      // amber-500
const SELECTED_COLOR = 'rgba(99, 102, 241, 0.9)'     // indigo-500
const LABEL_BG_ALPHA = 0.72

export function PhotoAnnotationCanvas({
  src,
  detections,
  onSelect,
  className = '',
}: PhotoAnnotationCanvasProps) {
  const imgRef = useRef<HTMLImageElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 })

  const bboxDetections = detections.filter((d) => d.bbox)

  function draw(naturalW: number, naturalH: number, displayW: number, displayH: number) {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = displayW
    canvas.height = displayH
    ctx.clearRect(0, 0, displayW, displayH)

    const scaleX = displayW / naturalW
    const scaleY = displayH / naturalH

    for (const det of bboxDetections) {
      const bbox = det.bbox!
      const x = bbox.x * naturalW * scaleX
      const y = bbox.y * naturalH * scaleY
      const w = bbox.w * naturalW * scaleX
      const h = bbox.h * naturalH * scaleY

      const isSelected = selected === det.id
      const strokeColor = isSelected
        ? SELECTED_COLOR
        : det.needs_review
          ? REVIEW_COLOR
          : CONFIRMED_COLOR

      // Box
      ctx.strokeStyle = strokeColor
      ctx.lineWidth = isSelected ? 3 : 2
      ctx.strokeRect(x, y, w, h)

      // Semi-transparent fill for selected
      if (isSelected) {
        ctx.fillStyle = strokeColor.replace('0.9', '0.12')
        ctx.fillRect(x, y, w, h)
      }

      // Label background
      const label = `${det.fixture_type} (${(det.confidence * 100).toFixed(0)}%)`
      ctx.font = '11px system-ui, sans-serif'
      const textW = ctx.measureText(label).width
      ctx.fillStyle = strokeColor.replace(/[\d.]+\)$/, `${LABEL_BG_ALPHA})`)
      ctx.fillRect(x, y > 14 ? y - 16 : y, textW + 8, 16)

      // Label text
      ctx.fillStyle = '#fff'
      ctx.fillText(label, x + 4, y > 14 ? y - 4 : y + 12)
    }
  }

  useEffect(() => {
    const img = imgRef.current
    if (!img || imgSize.w === 0) return
    draw(img.naturalWidth, img.naturalHeight, imgSize.w, imgSize.h)
  }, [selected, bboxDetections, imgSize]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleImageLoad() {
    const img = imgRef.current
    if (!img) return
    setImgSize({ w: img.clientWidth, h: img.clientHeight })
  }

  function handleCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current
    const img = imgRef.current
    if (!canvas || !img) return

    const rect = canvas.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const clickY = e.clientY - rect.top
    const scaleX = img.naturalWidth / canvas.width
    const scaleY = img.naturalHeight / canvas.height

    for (const det of bboxDetections) {
      const bbox = det.bbox!
      const x = bbox.x * img.naturalWidth / scaleX
      const y = bbox.y * img.naturalHeight / scaleY
      const w = bbox.w * img.naturalWidth / scaleX
      const h = bbox.h * img.naturalHeight / scaleY

      if (clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + h) {
        setSelected(det.id === selected ? null : det.id)
        onSelect?.(det)
        return
      }
    }
    setSelected(null)
  }

  return (
    <div className={`relative inline-block ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        src={src}
        alt="Blueprint detection overlay"
        className="block max-w-full"
        onLoad={handleImageLoad}
      />
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        className="absolute inset-0 cursor-crosshair"
        style={{ width: imgSize.w, height: imgSize.h }}
        aria-label="Detection annotation overlay"
      />
      {bboxDetections.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="bg-black/40 text-white text-xs px-2 py-1 rounded">No bounding box data</span>
        </div>
      )}
    </div>
  )
}
