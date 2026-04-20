'use client'

import { useState, useCallback, useMemo, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Upload, Trash2, Download } from 'lucide-react'
import {
  suppliersApi,
  downloadDocument,
  type DocumentItem,
} from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'
import { useDocuments, useUploadDocument, useDeleteDocument } from '@/lib/hooks'
import { PageIntro } from '@/components/layout/PageIntro'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { Badge } from '@/components/ui/Badge'
import { SearchInput } from '@/components/ui/SearchInput'
import { Select } from '@/components/ui/Select'
import dynamic from 'next/dynamic'
import { Modal } from '@/components/ui/Modal'

const ConfirmDialog = dynamic(() => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })), { ssr: false })
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Tooltip } from '@/components/ui/Tooltip'
import { useToast } from '@/components/ui/Toast'

// ─── Constants ────────────────────────────────────────────────────────────────

const DOC_TYPE_OPTIONS = [
  { value: 'supplier_catalog', label: 'Supplier Catalog' },
  { value: 'price_sheet', label: 'Price Sheet' },
  { value: 'specification', label: 'Specification' },
  { value: 'manual', label: 'Manual' },
  { value: 'other', label: 'Other' },
]

const DOC_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  DOC_TYPE_OPTIONS.map(o => [o.value, o.label]),
)

const STATUS_BADGE: Record<string, 'warning' | 'success' | 'danger' | 'neutral'> = {
  processing: 'warning',
  ready: 'success',
  error: 'danger',
}

function prettyDocType(t: string) {
  return DOC_TYPE_LABELS[t] ?? t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function prettyStatus(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DocumentsPage() {
  const toast = useToast()

  // ── State ──
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<DocumentItem | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  // Upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadDocType, setUploadDocType] = useState('')
  const [uploadSupplierId, setUploadSupplierId] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Queries ──
  const {
    data: documents = [],
    isLoading,
    isError,
    refetch,
  } = useDocuments()

  const { data: suppliersRaw } = useQuery({
    queryKey: ['suppliers-list'],
    queryFn: async () => {
      const res = await suppliersApi.list()
      return res.data
    },
  })

  const supplierOptions = useMemo(() => {
    if (!Array.isArray(suppliersRaw)) return []
    return suppliersRaw.map((s: { id: number; name: string }) => ({
      value: String(s.id),
      label: s.name,
    }))
  }, [suppliersRaw])

  // ── Mutations ──
  const uploadMutation = useUploadDocument()
  const deleteMutation = useDeleteDocument()

  // ── Handlers ──
  const handleDownload = useCallback(async (doc: DocumentItem) => {
    setDownloadingId(doc.id)
    try {
      await downloadDocument(doc.id, doc.name)
    } catch {
      toast.error('Download failed', 'Could not download the document. Please try again.')
    } finally {
      setDownloadingId(null)
    }
  }, [toast])
  const resetUploadForm = useCallback(() => {
    setUploadFile(null)
    setUploadDocType('')
    setUploadSupplierId('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [])

  const handleUploadSubmit = useCallback(() => {
    if (!uploadFile || !uploadDocType) return
    uploadMutation.mutate(
      {
        file: uploadFile,
        docType: uploadDocType,
        supplierId: uploadSupplierId || undefined,
      },
      {
        onSuccess: () => {
          toast.success('Document uploaded', 'Your document is being processed.')
          resetUploadForm()
          setUploadOpen(false)
        },
        onError: () => {
          toast.error('Upload failed', 'Could not upload document. Please try again.')
        },
      },
    )
  }, [uploadFile, uploadDocType, uploadSupplierId, uploadMutation, toast, resetUploadForm])

  const handleUploadClose = useCallback(() => {
    if (!uploadMutation.isPending) {
      setUploadOpen(false)
      resetUploadForm()
    }
  }, [uploadMutation.isPending, resetUploadForm])

  // ── Filtering ──
  const filtered = useMemo(() => {
    return documents.filter((doc: DocumentItem) => {
      const q = search.toLowerCase()
      const matchSearch = !q || doc.name.toLowerCase().includes(q)
      const matchType = !typeFilter || doc.doc_type === typeFilter
      const matchStatus = !statusFilter || doc.status === statusFilter
      return matchSearch && matchType && matchStatus
    })
  }, [documents, search, typeFilter, statusFilter])

  // ── Table columns ──
  const columns: Column<DocumentItem>[] = useMemo(
    () => [
      {
        key: 'name',
        header: 'Name',
        sortable: true,
        render: (row) => (
          <span className="font-medium text-[color:var(--ink)] truncate block max-w-[200px]">
            {row.name}
          </span>
        ),
      },
      {
        key: 'doc_type',
        header: 'Type',
        render: (row) => (
          <Badge variant="accent" size="sm">
            {prettyDocType(row.doc_type)}
          </Badge>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        render: (row) => (
          <Badge
            variant={STATUS_BADGE[row.status] ?? 'neutral'}
            size="sm"
            dot
          >
            {prettyStatus(row.status)}
          </Badge>
        ),
      },
      {
        key: 'supplier_name',
        header: 'Supplier',
        render: (row) => (
          <span className="text-[color:var(--muted-ink)]">
            {row.supplier_name ?? '—'}
          </span>
        ),
      },
      {
        key: 'created_at',
        header: 'Uploaded',
        render: (row) => (
          <span className="text-[color:var(--muted-ink)] text-xs tabular-nums">
            {formatRelativeTime(row.created_at)}
          </span>
        ),
      },
      {
        key: 'actions',
        header: '',
        width: '88px',
        align: 'right',
        render: (row) => (
          <div className="flex items-center justify-end gap-1">
            <Tooltip content="Download document">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  void handleDownload(row)
                }}
                disabled={downloadingId === row.id}
                className="inline-flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] transition-colors disabled:opacity-50"
                aria-label={`Download ${row.name}`}
              >
                <Download size={14} />
              </button>
            </Tooltip>
            <Tooltip content="Delete document">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setDeleteTarget(row)
                }}
                className="inline-flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] hover:bg-[hsl(var(--danger)/0.1)] hover:text-[hsl(var(--danger))] transition-colors"
                aria-label={`Delete ${row.name}`}
              >
                <Trash2 size={14} />
              </button>
            </Tooltip>
          </div>
        ),
      },
    ],
    [downloadingId, handleDownload],
  )

  // ── Render ──
  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Document Management"
          title="Manage uploaded documents."
          description="Upload, search, and manage supplier catalogs, price sheets, and specs."
          actions={
            <button
              onClick={() => setUploadOpen(true)}
              className="btn-primary flex items-center gap-2 px-4 py-2.5"
            >
              <Upload size={15} />
              Upload Document
            </button>
          }
        >
          {/* Filter bar */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Search documents…"
              className="flex-1"
            />
            <Select
              options={[{ value: '', label: 'All types' }, ...DOC_TYPE_OPTIONS]}
              value={typeFilter}
              onChange={setTypeFilter}
              placeholder="All types"
              size="md"
              className="sm:w-44"
            />
            <Select
              options={[
                { value: '', label: 'All statuses' },
                { value: 'processing', label: 'Processing' },
                { value: 'ready', label: 'Ready' },
                { value: 'error', label: 'Error' },
              ]}
              value={statusFilter}
              onChange={setStatusFilter}
              placeholder="All statuses"
              size="md"
              className="sm:w-40"
            />
          </div>
        </PageIntro>

        <div className="mt-4">
          {isError && !isLoading && (
            <ErrorState
              message="Could not load documents"
              onRetry={() => void refetch()}
              className="card"
            />
          )}

          {!isLoading && !isError && filtered.length === 0 && documents.length === 0 && (
            <EmptyState
              icon={<FileText size={28} />}
              title="No documents yet"
              description="Upload your first document to get started."
              action={
                <button onClick={() => setUploadOpen(true)} className="btn-primary text-xs px-3 py-2 flex items-center gap-1.5">
                  <Upload size={13} />
                  Upload Document
                </button>
              }
              className="card"
            />
          )}

          {!isLoading && !isError && filtered.length === 0 && documents.length > 0 && (
            <EmptyState
              icon={<FileText size={28} />}
              title="No documents match your filters"
              description="Try adjusting your search or filters."
              action={
                <button
                  onClick={() => { setSearch(''); setTypeFilter(''); setStatusFilter('') }}
                  className="btn-ghost text-xs"
                >
                  Clear filters
                </button>
              }
              className="card"
            />
          )}

          {(isLoading || filtered.length > 0) && (
            <DataTable
              columns={columns}
              data={filtered}
              keyExtractor={(row) => row.id}
              loading={isLoading}
              emptyMessage="No documents to display"
              stickyHeader
            />
          )}
        </div>
      </div>

      {/* ── Upload Modal ── */}
      <Modal
        open={uploadOpen}
        onClose={handleUploadClose}
        title="Upload Document"
        description="Upload a document for processing. Supported formats: PDF, CSV, XLSX."
        size="md"
      >
        <div className="space-y-4">
          {/* File picker */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-[color:var(--ink)]">
              File
            </label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-6 transition-colors hover:border-[color:var(--accent)]"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  fileInputRef.current?.click()
                }
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.csv,.xlsx,.xls"
                className="hidden"
                aria-label="Choose file to upload"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) setUploadFile(f)
                }}
              />
              <div className="text-center">
                {uploadFile ? (
                  <p className="text-sm font-medium text-[color:var(--ink)]">{uploadFile.name}</p>
                ) : (
                  <p className="text-sm text-[color:var(--muted-ink)]">
                    Click to choose a file
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Doc type */}
          <Select
            label="Document Type"
            options={DOC_TYPE_OPTIONS}
            value={uploadDocType}
            onChange={setUploadDocType}
            placeholder="Select type…"
          />

          {/* Supplier (optional) */}
          {supplierOptions.length > 0 && (
            <Select
              label="Supplier (optional)"
              options={supplierOptions}
              value={uploadSupplierId}
              onChange={setUploadSupplierId}
              placeholder="None"
              clearable
              searchable
            />
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleUploadClose}
              disabled={uploadMutation.isPending}
              className="btn-ghost px-4 py-2.5 text-sm"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleUploadSubmit}
              disabled={!uploadFile || !uploadDocType || uploadMutation.isPending}
              className="btn-primary px-4 py-2.5 text-sm flex items-center gap-2"
            >
              {uploadMutation.isPending ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Uploading…
                </>
              ) : (
                <>
                  <Upload size={14} />
                  Upload
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Delete Confirm ── */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id, {
            onSuccess: () => {
              toast.success('Document deleted')
              setDeleteTarget(null)
            },
            onError: () => {
              toast.error('Delete failed', 'Could not delete document. Please try again.')
            },
          })
        }}
        title="Delete document"
        description={`Are you sure you want to delete "${deleteTarget?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
