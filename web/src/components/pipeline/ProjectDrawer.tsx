'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, BriefcaseBusiness, UserRound, Phone, Mail, MapPin,
  FileText, StickyNote, RefreshCw, Save, ExternalLink,
  Calendar, ChevronRight,
} from 'lucide-react'
import { format, isValid } from 'date-fns'
import { projectsApi } from '@/lib/api'
import { cn, formatCurrency } from '@/lib/utils'
import { useToast } from '@/components/ui/Toast'
import { Skeleton } from '@/components/ui/Skeleton'

interface EstimateSummary {
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
  city: string
  county: string
  state: string
  zip_code: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
  estimate_count: number
  estimates: EstimateSummary[]
}

const STATUS_COLORS: Record<string, string> = {
  lead:          'bg-white/[0.05] text-zinc-400 border-white/[0.08]',
  estimate_sent: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  won:           'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  lost:          'bg-red-500/10 text-red-400 border-red-500/20',
  in_progress:   'bg-amber-500/10 text-amber-400 border-amber-500/20',
  complete:      'bg-emerald-600/15 text-emerald-300 border-emerald-600/25',
}

const JOB_TYPE_CLASS: Record<string, string> = {
  service: 'badge-service',
  construction: 'badge-construction',
  commercial: 'badge-commercial',
}

function fmtDate(s: string) {
  const d = new Date(s)
  return isValid(d) ? format(d, 'MMM d, yyyy') : '—'
}

export function ProjectDrawer({
  projectId,
  onClose,
  onUpdated,
}: {
  projectId: number | null
  onClose: () => void
  onUpdated: (id: number, changes: Record<string, unknown>) => void
}) {
  const router = useRouter()
  const toast  = useToast()

  const [project,  setProject]  = useState<ProjectDetail | null>(null)
  const [loading,  setLoading]  = useState(false)
  const [saving,   setSaving]   = useState(false)
  const [editing,  setEditing]  = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [form,     setForm]     = useState({
    customer_name:  '',
    customer_phone: '',
    customer_email: '',
    address:        '',
    city:           '',
    county:         '',
    zip_code:       '',
    notes:          '',
  })

  useEffect(() => {
    if (!projectId) return
    const load = async () => {
      setLoading(true)
      setEditing(false)
      try {
        const res = await projectsApi.get(projectId)
        const p = res.data as ProjectDetail
        setProject(p)
        setForm({
          customer_name:  p.customer_name  ?? '',
          customer_phone: p.customer_phone ?? '',
          customer_email: p.customer_email ?? '',
          address:        p.address        ?? '',
          city:           p.city           ?? '',
          county:         p.county         ?? '',
          zip_code:       p.zip_code       ?? '',
          notes:          p.notes          ?? '',
        })
      } catch {
        toast.error('Could not load project details')
        onClose()
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k: keyof typeof form, v: string) => setForm(p => ({ ...p, [k]: v }))

  const handleSave = async () => {
    if (!project) return
    setSaving(true)
    setSaveError(null)
    try {
      await projectsApi.update(project.id, {
        customer_name:  form.customer_name  || undefined,
        customer_phone: form.customer_phone || undefined,
        customer_email: form.customer_email || undefined,
        city:           form.city           || undefined,
        county:         form.county         || undefined,
        notes:          form.notes          || undefined,
      })
      // Update local project state
      setProject(prev => prev ? {
        ...prev,
        customer_name:  form.customer_name  || null,
        customer_phone: form.customer_phone || null,
        customer_email: form.customer_email || null,
        city:           form.city,
        county:         form.county,
        notes:          form.notes          || null,
      } : prev)
      onUpdated(project.id, {
        customer_name: form.customer_name || null,
        city:          form.city,
        county:        form.county,
      })
      toast.success('Project updated')
      setEditing(false)
      setSaveError(null)
    } catch (err) {
      const msg = err instanceof Error && err.message ? err.message : 'Failed to save changes'
      setSaveError(msg)
      toast.error('Could not save project', msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      {projectId !== null && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            className="fixed inset-y-0 right-0 w-full max-w-sm bg-[#0a0a0a] border-l border-white/[0.08] z-50 flex flex-col shadow-2xl"
            style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 16px)' }}
            aria-label="Project details drawer"
            role="complementary"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-white/[0.07] shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center" aria-hidden="true">
                  <BriefcaseBusiness size={14} className="text-blue-400" />
                </div>
                <span className="text-sm font-bold text-white">Project Details</span>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-xl hover:bg-white/[0.07] text-zinc-500 hover:text-zinc-200 transition-colors"
                aria-label="Close drawer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {loading && (
                <div className="p-5 space-y-4">
                  <Skeleton variant="text" className="h-6 w-3/4" />
                  <Skeleton variant="text" className="h-4 w-1/2" />
                  <Skeleton variant="card" className="h-24" />
                  <Skeleton variant="card" className="h-32" />
                </div>
              )}

              {!loading && project && (
                <div className="p-5 space-y-5">

                  {/* Project identity */}
                  <div>
                    <h2 className="text-base font-bold text-white leading-tight mb-2">{project.name}</h2>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={cn('badge', JOB_TYPE_CLASS[project.job_type] ?? 'badge-service')}>
                        {project.job_type}
                      </span>
                      <span className={cn('badge border', STATUS_COLORS[project.status] ?? STATUS_COLORS.lead)}>
                        {project.status.replace('_', ' ')}
                      </span>
                      <span className="text-[11px] text-zinc-600 flex items-center gap-1">
                        <Calendar size={10} />
                        {fmtDate(project.created_at)}
                      </span>
                    </div>
                  </div>

                  {/* Customer info */}
                  <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden">
                    <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-white/[0.05]">
                      <div className="flex items-center gap-2">
                        <UserRound size={13} className="text-zinc-500" aria-hidden="true" />
                        <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Customer</span>
                      </div>
                      <button
                        onClick={() => setEditing(e => !e)}
                        className="text-[11px] font-semibold text-blue-400 hover:text-blue-300 transition-colors"
                        aria-label={editing ? 'Cancel editing' : 'Edit customer info'}
                        aria-expanded={editing}
                      >
                        {editing ? 'Cancel' : 'Edit'}
                      </button>
                    </div>

                    {editing ? (
                      <div className="p-3.5 space-y-3">
                        <div>
                          <label htmlFor="drawer-customer-name" className="block text-[10px] font-bold text-zinc-600 uppercase tracking-wider mb-1">Name</label>
                          <input id="drawer-customer-name" value={form.customer_name} onChange={e => set('customer_name', e.target.value)} className="input text-sm" placeholder="Customer name" autoComplete="name" />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label htmlFor="drawer-customer-phone" className="block text-[10px] font-bold text-zinc-600 uppercase tracking-wider mb-1">Phone</label>
                            <input id="drawer-customer-phone" value={form.customer_phone} onChange={e => set('customer_phone', e.target.value)} className="input text-sm" placeholder="(214) 555-0100" autoComplete="tel" />
                          </div>
                          <div>
                            <label htmlFor="drawer-customer-city" className="block text-[10px] font-bold text-zinc-600 uppercase tracking-wider mb-1">City</label>
                            <input id="drawer-customer-city" value={form.city} onChange={e => set('city', e.target.value)} className="input text-sm" placeholder="Dallas" autoComplete="address-level2" />
                          </div>
                        </div>
                        <div>
                          <label htmlFor="drawer-customer-email" className="block text-[10px] font-bold text-zinc-600 uppercase tracking-wider mb-1">Email</label>
                          <input id="drawer-customer-email" type="email" value={form.customer_email} onChange={e => set('customer_email', e.target.value)} className="input text-sm" placeholder="customer@email.com" autoComplete="email" />
                        </div>
                        <div>
                          <label htmlFor="drawer-customer-county" className="block text-[10px] font-bold text-zinc-600 uppercase tracking-wider mb-1">County</label>
                          <input id="drawer-customer-county" value={form.county} onChange={e => set('county', e.target.value)} className="input text-sm" placeholder="Dallas" />
                        </div>
                      </div>
                    ) : (
                      <div className="p-3.5 space-y-2.5">
                        {[
                          { icon: UserRound, label: project.customer_name || '—', aria: 'Customer name' },
                          { icon: Phone,    label: project.customer_phone || '—', aria: 'Phone number' },
                          { icon: Mail,     label: project.customer_email || '—', aria: 'Email address' },
                          { icon: MapPin,   label: [project.city, project.county + ' Co.', project.state].filter(Boolean).join(', ') || '—', aria: 'Address' },
                        ].map(({ icon: Icon, label, aria }) => (
                          <div key={aria} className="flex items-center gap-2.5" aria-label={`${aria}: ${label}`}>
                            <Icon size={12} className="text-zinc-600 shrink-0" aria-hidden="true" />
                            <span className="text-xs text-zinc-300 truncate">{label}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Notes */}
                  <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden">
                    <div className="flex items-center gap-2 px-3.5 py-2.5 border-b border-white/[0.05]">
                      <StickyNote size={13} className="text-zinc-500" />
                      <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Notes</span>
                    </div>
                    {editing ? (
                      <div className="p-3.5">
                        <textarea
                          value={form.notes}
                          onChange={e => set('notes', e.target.value)}
                          rows={3}
                          className="input resize-none text-sm w-full"
                          placeholder="Access notes, customer requests…"
                        />
                      </div>
                    ) : (
                      <div className="px-3.5 py-3">
                        <p className="text-xs text-zinc-400 leading-relaxed whitespace-pre-wrap">
                          {project.notes || <span className="text-zinc-700 italic">No notes</span>}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Save button */}
                  {editing && (
                    <motion.button
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={handleSave}
                      disabled={saving}
                      className="btn-primary w-full justify-center"
                    >
                      {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
                      {saving ? 'Saving…' : 'Save Changes'}
                    </motion.button>
                  )}
                  {editing && saveError && (
                    <div
                      role="alert"
                      aria-live="polite"
                      className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-400"
                    >
                      {saveError}
                    </div>
                  )}

                  {/* Linked Estimates */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <FileText size={13} className="text-zinc-500" />
                      <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                        Estimates
                      </span>
                      <span className="ml-auto text-[11px] text-zinc-600">
                        {project.estimates.length}
                      </span>
                    </div>

                    {project.estimates.length === 0 ? (
                      <div className="bg-white/[0.02] border border-dashed border-white/[0.07] rounded-xl p-5 text-center">
                        <p className="text-xs text-zinc-600">No estimates linked to this project yet.</p>
                        <button
                          onClick={() => router.push('/estimator')}
                          className="btn-ghost text-xs mt-3 mx-auto"
                        >
                          Open Estimator
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {project.estimates.map(est => (
                          <button
                            key={est.id}
                            onClick={() => router.push(`/estimates/${est.id}`)}
                            className="w-full text-left bg-white/[0.02] border border-white/[0.06] hover:border-white/10 hover:bg-white/[0.04] rounded-xl px-3.5 py-3 transition-colors group"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="min-w-0 flex-1">
                                <div className="text-xs font-semibold text-zinc-200 truncate">
                                  {est.title || `Estimate #${est.id}`}
                                </div>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className="text-[10px] text-zinc-600">{fmtDate(est.created_at)}</span>
                                  <span className={cn('badge text-[9px] py-px', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>
                                    {est.job_type}
                                  </span>
                                </div>
                              </div>
                              <div className="text-right shrink-0">
                                <div className="text-sm font-extrabold tabular-nums" style={{ color: 'hsl(38 90% 62%)' }}>{formatCurrency(est.grand_total)}</div>
                                <ChevronRight size={12} className="text-zinc-700 group-hover:text-zinc-400 transition-colors ml-auto mt-0.5" />
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                </div>
              )}
            </div>

            {/* Footer action */}
            {!loading && project && (
              <div className="px-5 py-3 border-t border-white/[0.07] shrink-0">
                <button
                  onClick={() => router.push('/estimator')}
                  className="btn-secondary w-full justify-center text-xs"
                >
                  <ExternalLink size={13} />
                  Create New Estimate
                </button>
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
