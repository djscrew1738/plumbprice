'use client'

import { useState } from 'react'
import { RefreshCw, Check } from 'lucide-react'
import { projectsApi, type ProjectPipelineItem } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Select, type SelectOption } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'

const JOB_TYPE_OPTIONS: SelectOption[] = [
  { value: 'service', label: 'Service' },
  { value: 'construction', label: 'Construction' },
  { value: 'commercial', label: 'Commercial' },
]

const COUNTY_OPTIONS: SelectOption[] = [
  { value: 'Dallas', label: 'Dallas' },
  { value: 'Tarrant', label: 'Tarrant' },
  { value: 'Collin', label: 'Collin' },
  { value: 'Denton', label: 'Denton' },
  { value: 'Rockwall', label: 'Rockwall' },
  { value: 'Parker', label: 'Parker' },
]

export interface CreateProjectModalProps {
  open: boolean
  onClose: () => void
  onCreated: (project: ProjectPipelineItem) => void
}

export function CreateProjectModal({ open, onClose, onCreated }: CreateProjectModalProps) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    name: '',
    job_type: 'service',
    customer_name: '',
    county: 'Dallas',
    notes: '',
  })

  const set = (field: string, val: string) =>
    setForm(prev => ({ ...prev, [field]: val }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    try {
      const res = await projectsApi.create({
        name:          form.name.trim(),
        job_type:      form.job_type,
        customer_name: form.customer_name.trim() || undefined,
        county:        form.county,
        notes:         form.notes.trim() || undefined,
      })
      const raw = res.data as unknown as { project?: ProjectPipelineItem } | ProjectPipelineItem
      const project = ('project' in raw && raw.project) ? raw.project : raw as ProjectPipelineItem
      onCreated(project)
    } catch {
      toast.error('Could not create project', 'Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New Project"
      size="md"
    >
      <form
        onSubmit={e => void handleSubmit(e)}
        className="space-y-4"
      >
        <Input
          label="Project Name *"
          autoFocus
          value={form.name}
          onChange={e => set('name', e.target.value)}
          placeholder="e.g. 123 Main St — Water Heater"
          required
          aria-required="true"
          size="md"
        />

        <div className="grid grid-cols-2 gap-3">
          <Select
            label="Job Type"
            options={JOB_TYPE_OPTIONS}
            value={form.job_type}
            onChange={val => set('job_type', val)}
            size="md"
          />
          <Select
            label="County"
            options={COUNTY_OPTIONS}
            value={form.county}
            onChange={val => set('county', val)}
            size="md"
          />
        </div>

        <Input
          label="Customer Name"
          value={form.customer_name}
          onChange={e => set('customer_name', e.target.value)}
          placeholder="Optional"
          size="md"
        />

        <Textarea
          label="Notes"
          value={form.notes}
          onChange={e => set('notes', e.target.value)}
          placeholder="Optional job notes…"
          rows={2}
        />

        <div className="flex items-center justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary min-h-0 py-2">
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !form.name.trim()}
            className="btn-primary min-h-0 py-2 disabled:opacity-50"
          >
            {saving ? (
              <RefreshCw size={13} className="animate-spin" aria-hidden="true" />
            ) : (
              <Check size={13} aria-hidden="true" />
            )}
            {saving ? 'Creating…' : 'Create Project'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
