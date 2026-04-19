'use client'

import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, BriefcaseBusiness, MapPin, Phone, Mail, FileText,
  CalendarDays, User2, StickyNote, ExternalLink,
} from 'lucide-react'
import { projectsApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'
import { format, isValid } from 'date-fns'

interface ProjectEstimate {
  id: number
  title: string
  job_type: string
  status: string
  grand_total: number
  confidence_label: string
  county: string
  created_at: string
}

interface ProjectDetail {
  id: number
  name: string
  job_type: string
  status: string
  customer_name: string | null
  customer_phone: string | null
  customer_email: string | null
  address: string | null
  city: string | null
  county: string | null
  state: string | null
  zip_code: string | null
  notes: string | null
  created_at: string
  updated_at: string
  estimate_count: number
  estimates: ProjectEstimate[]
}

const STAGE_VARIANT: Record<string, 'success' | 'danger' | 'info' | 'warning' | 'neutral'> = {
  lead: 'neutral',
  estimate_sent: 'info',
  won: 'success',
  lost: 'danger',
}

const STAGE_LABEL: Record<string, string> = {
  lead: 'Lead',
  estimate_sent: 'Estimate Sent',
  won: 'Won',
  lost: 'Lost',
}

const ESTIMATE_STATUS_VARIANT: Record<string, 'neutral' | 'info' | 'success' | 'danger'> = {
  draft: 'neutral',
  sent: 'info',
  accepted: 'success',
  rejected: 'danger',
}

function formatDate(str: string) {
  const d = new Date(str)
  return isValid(d) ? format(d, 'MMM d, yyyy') : '—'
}

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = Number(params?.id)

  const { data, isLoading, error } = useQuery({
    queryKey: ['project', id],
    queryFn: async () => (await projectsApi.get(id)).data as ProjectDetail,
    enabled: !isNaN(id),
  })

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton variant="card" className="h-40" />
        <Skeleton variant="card" className="h-32" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6">
        <ErrorState message="Could not load project" onRetry={() => router.back()} />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
      {/* Back button */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Pipeline
      </button>

      {/* Project header */}
      <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5 space-y-4">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
            <BriefcaseBusiness size={18} />
          </span>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-bold text-[color:var(--ink)] leading-tight">{data.name}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <Badge variant="neutral" size="sm" className="capitalize">{data.job_type}</Badge>
              <Badge variant={STAGE_VARIANT[data.status] ?? 'neutral'} size="sm">
                {STAGE_LABEL[data.status] ?? data.status}
              </Badge>
            </div>
          </div>
        </div>

        {/* Customer info */}
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {data.customer_name && (
            <div className="flex items-center gap-2 text-[color:var(--muted-ink)]">
              <User2 size={14} className="shrink-0" />
              <span className="truncate text-[color:var(--ink)]">{data.customer_name}</span>
            </div>
          )}
          {data.customer_phone && (
            <a
              href={`tel:${data.customer_phone}`}
              className="flex items-center gap-2 text-[color:var(--muted-ink)] hover:text-[color:var(--accent-strong)] transition-colors"
            >
              <Phone size={14} className="shrink-0" />
              <span className="truncate">{data.customer_phone}</span>
            </a>
          )}
          {data.customer_email && (
            <a
              href={`mailto:${data.customer_email}`}
              className="flex items-center gap-2 text-[color:var(--muted-ink)] hover:text-[color:var(--accent-strong)] transition-colors"
            >
              <Mail size={14} className="shrink-0" />
              <span className="truncate">{data.customer_email}</span>
            </a>
          )}
          {(data.city || data.county) && (
            <div className="flex items-center gap-2 text-[color:var(--muted-ink)]">
              <MapPin size={14} className="shrink-0" />
              <span className="truncate">{[data.city, data.county, data.state].filter(Boolean).join(', ')}</span>
            </div>
          )}
          <div className="flex items-center gap-2 text-[color:var(--muted-ink)]">
            <CalendarDays size={14} className="shrink-0" />
            <span>Created {formatDate(data.created_at)}</span>
          </div>
        </div>

        {data.notes && (
          <div className="flex gap-2 pt-2 border-t border-[color:var(--line)]">
            <StickyNote size={14} className="shrink-0 mt-0.5 text-[color:var(--muted-ink)]" />
            <p className="text-sm text-[color:var(--muted-ink)] whitespace-pre-line">{data.notes}</p>
          </div>
        )}
      </div>

      {/* Estimates list */}
      <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-[color:var(--line)]">
          <FileText size={16} className="text-[color:var(--accent-strong)]" />
          <h2 className="text-sm font-semibold text-[color:var(--ink)]">
            Estimates
            <span className="ml-2 text-xs font-normal text-[color:var(--muted-ink)]">({data.estimate_count})</span>
          </h2>
        </div>

        {data.estimates.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-[color:var(--muted-ink)]">
            No estimates yet for this project.
          </div>
        ) : (
          <ul className="divide-y divide-[color:var(--line)]">
            {data.estimates.map(est => (
              <li key={est.id}>
                <button
                  onClick={() => router.push(`/estimates/${est.id}`)}
                  className="w-full flex items-center gap-3 px-5 py-3.5 hover:bg-[color:var(--panel-strong)] transition-colors text-left group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[color:var(--ink)] truncate group-hover:text-[color:var(--accent-strong)] transition-colors">
                      {est.title}
                    </p>
                    <p className="text-xs text-[color:var(--muted-ink)] mt-0.5">{formatDate(est.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={cn(
                      'text-xs font-semibold tabular-nums',
                      est.status === 'accepted'
                        ? 'text-emerald-600'
                        : est.status === 'rejected'
                          ? 'text-red-500'
                          : 'text-[color:var(--ink)]',
                    )}>
                      {formatCurrency(est.grand_total)}
                    </span>
                    <Badge variant={ESTIMATE_STATUS_VARIANT[est.status] ?? 'neutral'} size="sm" className="capitalize">
                      {est.status}
                    </Badge>
                    <ExternalLink size={13} className="text-[color:var(--muted-ink)] opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
