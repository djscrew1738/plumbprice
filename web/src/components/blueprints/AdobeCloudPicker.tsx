'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Cloud, Unlink, Search, FileText, Loader2,
  AlertCircle, X, ExternalLink, RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { adobeApi, type AdobeFileItem } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

interface Props {
  /** Called after a file is successfully imported (with the new blueprint job_id). */
  /** Called after a file is successfully imported (with the new blueprint job_id). */
  onImported: (jobId: number, filename: string) => void
  /** Optional project to associate the import with. */
  projectId?: number
  className?: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return ''
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FileRow({
  file,
  importing,
  onImport,
}: {
  file: AdobeFileItem
  importing: boolean
  onImport: (file: AdobeFileItem) => void
}) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-lg border border-white/5',
        'hover:bg-white/5 transition-colors group',
      )}
    >
      <div className="flex-shrink-0 text-[hsl(var(--muted-foreground))]">
        {file.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={file.thumbnail_url}
            alt=""
            className="w-8 h-10 object-cover rounded border border-white/10"
          />
        ) : (
          <FileText className="w-8 h-8 opacity-50" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate text-[hsl(var(--foreground))]">{file.name}</p>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          {[formatDate(file.modified), formatBytes(file.size_bytes)].filter(Boolean).join(' · ')}
        </p>
      </div>

      <button
        onClick={() => onImport(file)}
        disabled={importing}
        className={cn(
          'flex-shrink-0 px-3 py-1.5 rounded-md text-xs font-medium',
          'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]',
          'opacity-0 group-hover:opacity-100 transition-opacity',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'flex items-center gap-1.5',
        )}
      >
        {importing ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <Cloud className="w-3 h-3" />
        )}
        Import
      </button>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function AdobeCloudPicker({ onImported, projectId, className }: Props) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [importingId, setImportingId] = useState<string | null>(null)
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout>>(null)

  // Check connection status
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['adobe', 'status'],
    queryFn: () => adobeApi.getStatus().then(r => r.data),
    staleTime: 30_000,
  })

  // List files (only when modal is open and connected)
  const {
    data: filesData,
    isLoading: filesLoading,
    isError: filesError,
    refetch: refetchFiles,
  } = useQuery({
    queryKey: ['adobe', 'files', search],
    queryFn: () => adobeApi.listFiles({ limit: 50, search: search || undefined }).then(r => r.data),
    enabled: open && !!status?.connected,
    staleTime: 60_000,
  })

  // Connect mutation — get auth URL then redirect
  const connectMutation = useMutation({
    mutationFn: () => adobeApi.getAuthUrl().then(r => r.data),
    onSuccess: ({ auth_url }) => {
      window.location.href = auth_url
    },
    onError: () => {
      toast.error('Adobe not configured', 'Set ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET on the server.')
    },
  })

  // Disconnect mutation
  const disconnectMutation = useMutation({
    mutationFn: () => adobeApi.disconnect(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['adobe'] })
      setOpen(false)
      toast.success('Adobe disconnected')
    },
  })

  // Import mutation
  const importMutation = useMutation({
    mutationFn: (file: AdobeFileItem) =>
      adobeApi.importFile({
        asset_id: file.asset_id,
        filename: file.name,
        project_id: projectId,
      }).then(r => r.data),
    onSuccess: (data, file) => {
      setImportingId(null)
      setOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['blueprints'] })
      toast.success(`"${file.name}" imported`, 'Queued for AI analysis.')
      onImported(data.job_id, data.filename)
    },
    onError: () => {
      setImportingId(null)
      toast.error('Import failed', 'Could not download file from Adobe.')
    },
  })

  const handleImport = useCallback((file: AdobeFileItem) => {
    setImportingId(file.asset_id)
    importMutation.mutate(file)
  }, [importMutation])

  // Debounced search
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearch(value)
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    searchTimeoutRef.current = setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey: ['adobe', 'files'] })
    }, 400)
  }

  // Handle adobe_connected=1 or adobe_error= query params after OAuth redirect
  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (params.get('adobe_connected')) {
      void queryClient.invalidateQueries({ queryKey: ['adobe'] })
      toast.success('Adobe connected!')
      // Clean up URL
      const url = new URL(window.location.href)
      url.searchParams.delete('adobe_connected')
      window.history.replaceState({}, '', url.toString())
      setOpen(true)
    }
    if (params.get('adobe_error')) {
      toast.error('Connection failed', 'Adobe OAuth error. Please try again.')
      const url = new URL(window.location.href)
      url.searchParams.delete('adobe_error')
      window.history.replaceState({}, '', url.toString())
    }
  }, [queryClient, toast])

  // ── Not connected state ────────────────────────────────────────────────────
  if (!statusLoading && !status?.connected) {
    return (
      <button
        onClick={() => connectMutation.mutate()}
        disabled={connectMutation.isPending}
        className={cn(
          'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border',
          'border-[hsl(var(--border))] bg-[hsl(var(--card))]',
          'hover:bg-[hsl(var(--accent))] transition-colors',
          'disabled:opacity-60 disabled:cursor-not-allowed',
          className,
        )}
      >
        {connectMutation.isPending ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Cloud className="w-4 h-4 text-[#FF0000]" />
        )}
        Connect Adobe Cloud
      </button>
    )
  }

  // ── Connected state — picker button ───────────────────────────────────────
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        disabled={statusLoading}
        className={cn(
          'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border',
          'border-[hsl(var(--border))] bg-[hsl(var(--card))]',
          'hover:bg-[hsl(var(--accent))] transition-colors',
          'disabled:opacity-60 disabled:cursor-not-allowed',
          className,
        )}
      >
        <Cloud className="w-4 h-4 text-[#FF0000]" />
        Adobe Cloud
        {status?.adobe_email && (
          <span className="text-[hsl(var(--muted-foreground))] text-xs hidden sm:inline truncate max-w-[120px]">
            ({status.adobe_email})
          </span>
        )}
      </button>

      {/* ── Modal ───────────────────────────────────────────────────────────── */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          role="button"
          tabIndex={0}
          aria-label="Close dialog"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false) }}
          onKeyDown={(e) => { if ((e.key === 'Escape' || e.key === 'Enter') && e.target === e.currentTarget) setOpen(false) }}
        >
          <div
            className={cn(
              'w-full max-w-lg rounded-xl border border-white/10',
              'bg-[hsl(var(--background))] shadow-2xl',
              'flex flex-col max-h-[80vh]',
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Cloud className="w-5 h-5 text-[#FF0000]" />
                <h2 className="text-base font-semibold">Adobe Document Cloud</h2>
                {status?.adobe_email && (
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">{status.adobe_email}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => void refetchFiles()}
                  className="p-1.5 rounded-md hover:bg-white/10 transition-colors"
                  title="Refresh"
                >
                  <RefreshCw className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                </button>
                <button
                  onClick={() => disconnectMutation.mutate()}
                  disabled={disconnectMutation.isPending}
                  className="p-1.5 rounded-md hover:bg-white/10 transition-colors text-[hsl(var(--muted-foreground))] hover:text-red-400"
                  title="Disconnect Adobe account"
                >
                  <Unlink className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded-md hover:bg-white/10 transition-colors"
                >
                  <X className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                </button>
              </div>
            </div>

            {/* Search */}
            <div className="p-4 border-b border-white/5">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <input
                  type="text"
                  placeholder="Search floorplans..."
                  value={search}
                  onChange={handleSearchChange}
                  className={cn(
                    'w-full pl-9 pr-4 py-2 rounded-lg text-sm',
                    'bg-[hsl(var(--card))] border border-white/10',
                    'placeholder:text-[hsl(var(--muted-foreground))]',
                    'focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/50',
                  )}
                />
              </div>
            </div>

            {/* File list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-1">
              {filesLoading && (
                <div className="flex flex-col items-center gap-3 py-12 text-[hsl(var(--muted-foreground))]">
                  <Loader2 className="w-6 h-6 animate-spin" />
                  <span className="text-sm">Loading your Adobe files…</span>
                </div>
              )}

              {filesError && (
                <div className="flex flex-col items-center gap-2 py-12 text-[hsl(var(--muted-foreground))]">
                  <AlertCircle className="w-6 h-6 text-red-400" />
                  <span className="text-sm text-center">
                    Could not load Adobe files. Your session may have expired.
                  </span>
                  <button
                    onClick={() => void refetchFiles()}
                    className="text-sm text-[hsl(var(--primary))] hover:underline"
                  >
                    Try again
                  </button>
                </div>
              )}

              {!filesLoading && !filesError && filesData?.files.length === 0 && (
                <div className="flex flex-col items-center gap-3 py-12 text-[hsl(var(--muted-foreground))]">
                  <FileText className="w-8 h-8 opacity-40" />
                  <span className="text-sm text-center">
                    No PDF files found in your Adobe Document Cloud.
                    {search && ' Try a different search term.'}
                  </span>
                  <a
                    href="https://acrobat.adobe.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-[hsl(var(--primary))] hover:underline"
                  >
                    Open Adobe Acrobat <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}

              {filesData?.files.map(file => (
                <FileRow
                  key={file.asset_id}
                  file={file}
                  importing={importingId === file.asset_id}
                  onImport={handleImport}
                />
              ))}
            </div>

            {/* Footer */}
            {filesData && filesData.total > filesData.files.length && (
              <div className="p-3 border-t border-white/5 text-xs text-center text-[hsl(var(--muted-foreground))]">
                Showing {filesData.files.length} of {filesData.total} PDF files
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
