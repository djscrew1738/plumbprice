'use client'

import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload,
  Download,
  Eye,
  CheckCircle2,
  AlertCircle,
  XCircle,
  FileSpreadsheet,
  Trash2,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'

import { DataTable, type Column } from '@/components/ui/DataTable'
import { Badge } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import { useBulkImportProducts, useBulkImportLabor, type BulkImportResult } from '@/lib/hooks'
import { cn } from '@/lib/utils'

type ImportType = 'products' | 'labor'

interface ImportRow {
  row_number: number
  status: string
  canonical_item?: string | null
  code?: string | null
  message: string
  details?: Record<string, unknown>
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  created: <CheckCircle2 size={14} className="text-emerald-500" />,
  updated: <CheckCircle2 size={14} className="text-blue-500" />,
  skipped: <Eye size={14} className="text-amber-500" />,
  error: <XCircle size={14} className="text-red-500" />,
}

const STATUS_VARIANT: Record<string, 'success' | 'info' | 'warning' | 'danger'> = {
  created: 'success',
  updated: 'info',
  skipped: 'warning',
  error: 'danger',
}

export function BulkImportPanel() {
  const toast = useToast()
  const [importType, setImportType] = useState<ImportType>('products')
  const [file, setFile] = useState<File | null>(null)
  const [dryRun, setDryRun] = useState(true)
  const [result, setResult] = useState<BulkImportResult | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const productMutation = useBulkImportProducts()
  const laborMutation = useBulkImportLabor()
  const isLoading = productMutation.isPending || laborMutation.isPending

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped && dropped.name.endsWith('.csv')) {
      setFile(dropped)
      setResult(null)
    } else {
      toast.error('Please upload a CSV file')
    }
  }, [toast])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      setFile(selected)
      setResult(null)
    }
  }, [])

  const handleImport = useCallback(async () => {
    if (!file) return
    setResult(null)

    const mutation = importType === 'products' ? productMutation : laborMutation
    const data = await mutation.mutateAsync({ file, dryRun })
    setResult(data)

    if (data.errors > 0) {
      toast.info(`Import preview: ${data.errors} errors found`)
    }
  }, [file, dryRun, importType, productMutation, laborMutation, toast])

  const handleDownloadTemplate = useCallback(() => {
    const endpoint = importType === 'products'
      ? '/admin/pricing/bulk-import/products/template'
      : '/admin/pricing/bulk-import/labor/template'

    const a = document.createElement('a')
    a.href = endpoint
    a.download = `${importType}_import_template.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }, [importType])

  const columns: Column<ImportRow>[] = [
    {
      key: 'row_number',
      header: 'Row',
      width: '60px',
      align: 'center',
      render: (row) => <span className="text-xs tabular-nums text-[color:var(--muted-ink)]">{row.row_number}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: '100px',
      render: (row) => (
        <div className="flex items-center gap-1.5">
          {STATUS_ICON[row.status] ?? <AlertCircle size={14} className="text-[color:var(--muted-ink)]" />}
          <Badge variant={STATUS_VARIANT[row.status] ?? 'neutral'} size="sm">{row.status}</Badge>
        </div>
      ),
    },
    {
      key: 'item',
      header: importType === 'products' ? 'Canonical Item' : 'Code',
      render: (row) => (
        <span className="font-mono text-xs truncate max-w-[200px] block">
          {importType === 'products' ? row.canonical_item : row.code}
        </span>
      ),
    },
    {
      key: 'message',
      header: 'Message',
      render: (row) => (
        <span className={cn(
          'text-sm',
          row.status === 'error' ? 'text-red-600 dark:text-red-400' : 'text-[color:var(--ink)]'
        )}>
          {row.message}
        </span>
      ),
    },
    {
      key: 'details',
      header: 'Details',
      width: '200px',
      render: (row) => {
        if (!row.details || Object.keys(row.details).length === 0) return null
        return (
          <div className="text-xs text-[color:var(--muted-ink)] space-y-0.5">
            {Object.entries(row.details).slice(0, 3).map(([k, v]) => (
              <div key={k} className="truncate"><span className="font-medium">{k}:</span> {String(v)}</div>
            ))}
          </div>
        )
      },
    },
  ]

  const rows = result?.rows ?? []
  const errorRows = rows.filter(r => r.status === 'error')
  const successRows = rows.filter(r => r.status === 'created' || r.status === 'updated')

  return (
    <div className="space-y-5">
      {/* Import type selector */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-1">
          <button
            onClick={() => { setImportType('products'); setFile(null); setResult(null) }}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              importType === 'products'
                ? 'bg-[color:var(--accent)] text-white shadow-sm'
                : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'
            )}
          >
            Supplier Products
          </button>
          <button
            onClick={() => { setImportType('labor'); setFile(null); setResult(null) }}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              importType === 'labor'
                ? 'bg-[color:var(--accent)] text-white shadow-sm'
                : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'
            )}
          >
            Labor Templates
          </button>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={handleDownloadTemplate}
          className="gap-1.5"
        >
          <Download size={14} />
          Download Template
        </Button>
      </div>

      {/* Upload area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'relative cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all',
          isDragging
            ? 'border-[color:var(--accent)] bg-[color:var(--accent)]/5'
            : 'border-[color:var(--line)] bg-[color:var(--panel)] hover:border-[color:var(--accent)]/50',
          file && 'border-solid border-[color:var(--accent)]/30'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          className="hidden"
        />
        <AnimatePresence mode="wait">
          {file ? (
            <motion.div
              key="file"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex flex-col items-center gap-2"
            >
              <FileSpreadsheet size={32} className="text-[color:var(--accent)]" />
              <p className="text-sm font-medium text-[color:var(--ink)]">{file.name}</p>
              <p className="text-xs text-[color:var(--muted-ink)]">
                {(file.size / 1024).toFixed(1)} KB
              </p>
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null) }}
                className="mt-1 flex items-center gap-1 text-xs text-red-500 hover:text-red-600"
              >
                <Trash2 size={12} /> Remove
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex flex-col items-center gap-2"
            >
              <Upload size={32} className="text-[color:var(--muted-ink)]" />
              <p className="text-sm font-medium text-[color:var(--ink)]">
                Drop a CSV file here, or click to browse
              </p>
              <p className="text-xs text-[color:var(--muted-ink)]">
                {importType === 'products'
                  ? 'Required: canonical_item, supplier_slug, name, cost'
                  : 'Required: code, name, category, base_hours'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            className="h-4 w-4 rounded border-[color:var(--line)] text-[color:var(--accent)] focus:ring-[color:var(--accent)]"
          />
          <span className="text-sm text-[color:var(--ink)]">Dry run (preview only)</span>
        </label>

        <Button
          onClick={handleImport}
          isLoading={isLoading}
          disabled={!file || isLoading}
          className="gap-1.5"
        >
          {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />}
          {dryRun ? 'Preview Import' : 'Run Import'}
        </Button>
      </div>

      {/* Results summary */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className={cn(
              'rounded-2xl border p-4',
              result.errors > 0
                ? 'border-amber-500/20 bg-amber-500/5'
                : 'border-emerald-500/20 bg-emerald-500/5'
            )}
          >
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-[color:var(--ink)]">{result.total_rows}</span>
                <span className="text-[color:var(--muted-ink)]">rows</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-500" />
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">{result.created}</span>
                <span className="text-[color:var(--muted-ink)]">created</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-blue-500" />
                <span className="font-semibold text-blue-600 dark:text-blue-400">{result.updated}</span>
                <span className="text-[color:var(--muted-ink)]">updated</span>
              </div>
              {result.errors > 0 && (
                <div className="flex items-center gap-1.5">
                  <XCircle size={14} className="text-red-500" />
                  <span className="font-semibold text-red-600 dark:text-red-400">{result.errors}</span>
                  <span className="text-[color:var(--muted-ink)]">errors</span>
                </div>
              )}
              {result.dry_run && (
                <Badge variant="warning" size="sm">DRY RUN</Badge>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error details */}
      <AnimatePresence>
        {errorRows.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
          >
            <h4 className="mb-2 text-sm font-semibold text-red-600 dark:text-red-400 flex items-center gap-1.5">
              <AlertCircle size={14} />
              Errors ({errorRows.length})
            </h4>
            <DataTable
              columns={columns}
              data={errorRows}
              keyExtractor={(r) => `error-${r.row_number}`}
              emptyMessage="No errors"
              className="max-h-[300px] overflow-auto"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Success details */}
      <AnimatePresence>
        {successRows.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
          >
            <h4 className="mb-2 text-sm font-semibold text-[color:var(--ink)]">
              Changes ({successRows.length})
            </h4>
            <DataTable
              columns={columns}
              data={successRows.slice(0, 100)}
              keyExtractor={(r) => `success-${r.row_number}`}
              emptyMessage="No changes"
              className="max-h-[400px] overflow-auto"
            />
            {successRows.length > 100 && (
              <p className="mt-2 text-xs text-[color:var(--muted-ink)] text-center">
                Showing first 100 of {successRows.length} rows
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
