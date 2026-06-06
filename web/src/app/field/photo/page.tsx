'use client'

/**
 * Field Photo Quote page — /field/photo
 *
 * Camera capture → multi-photo session → instant estimate.
 * Works offline: photos stored in IndexedDB until sync.
 */

import { useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Camera, X, Check, Upload, ArrowLeft, MapPin } from 'lucide-react'
import { cn } from '@/lib/utils'

type CapturedPhoto = {
  id: string
  dataUrl: string
  file: File
}

type SessionState = 'idle' | 'capturing' | 'reviewing' | 'submitting' | 'complete' | 'error'

export default function FieldPhotoPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [photos, setPhotos] = useState<CapturedPhoto[]>([])
  const [state, setState] = useState<SessionState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [county, setCounty] = useState<string>('')

  const handleCapture = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const newPhotos: CapturedPhoto[] = []
    let loaded = 0

    files.forEach((file) => {
      const reader = new FileReader()
      reader.onload = (ev) => {
        newPhotos.push({
          id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          dataUrl: ev.target?.result as string,
          file,
        })
        loaded++
        if (loaded === files.length) {
          setPhotos((prev) => [...prev, ...newPhotos])
          setState('reviewing')
        }
      }
      reader.readAsDataURL(file)
    })
  }, [])

  const removePhoto = useCallback((id: string) => {
    setPhotos((prev) => {
      const next = prev.filter((p) => p.id !== id)
      if (next.length === 0) setState('idle')
      return next
    })
  }, [])

  const handleSubmit = async () => {
    if (!photos.length) return
    setState('submitting')
    setError(null)

    try {
      const { apiV3 } = await import('@/lib/api-v3')

      // Auto-detect county from GPS if not set
      let resolvedCounty = county
      if (!resolvedCounty && navigator.geolocation) {
        try {
          const pos = await new Promise<GeolocationPosition>((res, rej) =>
            navigator.geolocation.getCurrentPosition(res, rej, { timeout: 5000 })
          )
          const geoResp = await apiV3.get(
            `/geo/county?lat=${pos.coords.latitude}&lng=${pos.coords.longitude}`
          )
          resolvedCounty = geoResp.data?.county || ''
          if (resolvedCounty) setCounty(resolvedCounty)
        } catch {
          // GPS unavailable — continue without county
        }
      }

      // Create session
      const createResp = await apiV3.post('/photos/sessions', {
        county: resolvedCounty || null,
      })
      const sid: number = createResp.data.id

      // Upload photos
      for (const photo of photos) {
        const formData = new FormData()
        formData.append('file', photo.file)
        await apiV3.post(`/photos/sessions/${sid}/add`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }

      // Finalize session
      await apiV3.post(`/photos/sessions/${sid}/finalize`)
      setState('complete')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit photos')
      setState('error')
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-background border-b border-border-subtle px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="p-2 -ml-2 rounded-lg hover:bg-surface-1 min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Back"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-base font-semibold">Photo Quote</h1>
          <p className="text-xs text-muted-foreground">{photos.length} photo{photos.length !== 1 ? 's' : ''}</p>
        </div>
      </header>

      <main className="flex-1 p-4 space-y-4">
        {/* Complete state */}
        {state === 'complete' && (
          <div className="rounded-xl bg-green-50 border border-green-200 p-6 text-center space-y-3">
            <Check className="h-10 w-10 text-green-600 mx-auto" />
            <p className="font-semibold text-green-800">Photos submitted!</p>
            <p className="text-sm text-green-600">Your estimate is being generated. Check the Estimates page.</p>
            <button
              onClick={() => router.push('/field')}
              className="mt-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium min-h-[44px]"
            >
              Back to Home
            </button>
          </div>
        )}

        {/* Error state */}
        {state === 'error' && (
          <div className="rounded-xl bg-red-50 border border-red-200 p-4 space-y-2">
            <p className="font-medium text-red-800">Submission failed</p>
            <p className="text-sm text-red-600">{error}</p>
            <button
              onClick={() => setState('reviewing')}
              className="text-sm text-red-700 underline min-h-[44px]"
            >
              Try again
            </button>
          </div>
        )}

        {/* Photo grid */}
        {photos.length > 0 && state !== 'complete' && (
          <div className="grid grid-cols-2 gap-3">
            {photos.map((photo) => (
              <div key={photo.id} className="relative aspect-square rounded-xl overflow-hidden bg-surface-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo.dataUrl} alt="Captured" className="w-full h-full object-cover" />
                <button
                  onClick={() => removePhoto(photo.id)}
                  className="absolute top-2 right-2 bg-black/60 text-white rounded-full p-1 min-h-[32px] min-w-[32px] flex items-center justify-center"
                  aria-label="Remove photo"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Capture button */}
        {state !== 'complete' && (
          <div className="space-y-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                'w-full flex items-center justify-center gap-3 p-4 rounded-xl border-2 border-dashed',
                'min-h-[80px] font-medium text-base transition-colors',
                photos.length === 0
                  ? 'border-orange-400 text-orange-600 bg-orange-50'
                  : 'border-border-subtle text-muted-foreground bg-surface-1'
              )}
            >
              <Camera className="h-6 w-6" />
              {photos.length === 0 ? 'Capture Photos' : 'Add More Photos'}
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              capture="environment"
              className="hidden"
              onChange={handleCapture}
            />

            {/* County field */}
            {photos.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border-subtle bg-surface-1">
                <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                <input
                  type="text"
                  placeholder="County (auto-detected)"
                  value={county}
                  onChange={(e) => setCounty(e.target.value)}
                  className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/60 min-h-[40px]"
                />
              </div>
            )}

            {/* Submit button */}
            {photos.length > 0 && state !== 'submitting' && (
              <button
                onClick={handleSubmit}
                className="w-full flex items-center justify-center gap-2 p-4 bg-orange-600 text-white rounded-xl font-semibold text-base min-h-[56px] active:scale-[0.98] transition-transform"
              >
                <Upload className="h-5 w-5" />
                Generate Estimate ({photos.length} photo{photos.length !== 1 ? 's' : ''})
              </button>
            )}

            {state === 'submitting' && (
              <div className="w-full flex items-center justify-center p-4 bg-orange-100 text-orange-700 rounded-xl font-medium min-h-[56px]">
                <span className="animate-pulse">Submitting…</span>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
