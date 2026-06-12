'use client'

import { useState } from 'react'
import { MapPin, Clock, Gauge, Wrench, Check, Pencil } from 'lucide-react'
import { haptic } from '@/lib/haptics'
import type { IntakeResultV3 } from '@/lib/api-v3'

interface IntakeCardProps {
  intake: IntakeResultV3
  onConfirm: (confirmed: IntakeResultV3) => void
}

const FIXTURE_LABELS: Record<string, string> = {
  toilet: 'Toilet',
  sink: 'Sink',
  faucet: 'Faucet',
  shower: 'Shower',
  bathtub: 'Bathtub',
  water_heater: 'Water heater',
  garbage_disposal: 'Disposal',
  dishwasher: 'Dishwasher',
  hose_bib: 'Hose bib',
  angle_stop: 'Angle stop',
  prv: 'PRV',
  backflow: 'Backflow',
  whole_house_filter: 'Whole-house filter',
}

function formatFixtures(fixtureCounts: Record<string, number>): string {
  return Object.entries(fixtureCounts)
    .filter(([, count]) => count > 0)
    .map(([key, count]) => `${count} ${FIXTURE_LABELS[key] || key}${count > 1 ? 's' : ''}`)
    .join(', ')
}

export function IntakeCard({ intake, onConfirm }: IntakeCardProps) {
  const [edited, setEdited] = useState<IntakeResultV3>({ ...intake })
  const [isEditing, setIsEditing] = useState(false)

  const handleConfirm = () => {
    haptic('tap')
    onConfirm(edited)
  }

  const chips: Array<{ key: string; label: string; icon?: React.ReactNode; value: string | null }> = [
    { key: 'fixtures', label: 'Fixtures', icon: <Wrench size={12} />, value: formatFixtures(edited.fixture_counts) },
    { key: 'location', label: 'Location', icon: <MapPin size={12} />, value: edited.location || null },
    { key: 'urgency', label: 'Urgency', icon: <Clock size={12} />, value: edited.urgency || null },
    { key: 'tier', label: 'Tier', icon: <Gauge size={12} />, value: edited.preferred_tier || null },
  ].filter(c => c.value)

  const fixtureEntries = Object.entries(edited.fixture_counts)

  return (
    <div className="my-3 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[12px] font-semibold uppercase tracking-wide text-[color:var(--accent-strong)]">
          We understood
        </p>
        <span className="text-[10px] text-[color:var(--muted-ink)]">
          {Math.round((edited.confidence || 0) * 100)}% confident
        </span>
      </div>

      {isEditing ? (
        <div className="space-y-2">
          {fixtureEntries.length > 0 ? (
            <div className="space-y-2">
              <p className="text-[11px] font-medium text-[color:var(--ink)]">Fixtures</p>
              {fixtureEntries.map(([key, count]) => (
                <label key={key} className="block text-[11px] text-[color:var(--muted-ink)]">
                  {FIXTURE_LABELS[key] || key}
                  <input
                    type="number"
                    min={0}
                    value={count}
                    onChange={e => {
                      const next = Math.max(0, parseInt(e.target.value, 10) || 0)
                      setEdited(prev => ({
                        ...prev,
                        fixture_counts: { ...prev.fixture_counts, [key]: next },
                      }))
                    }}
                    className="mt-1 w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-1 text-[12px] text-[color:var(--ink)]"
                  />
                </label>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-[color:var(--muted-ink)]">No fixtures detected.</p>
          )}
          <label className="block text-[11px] text-[color:var(--muted-ink)]">
            Location
            <input
              type="text"
              value={edited.location || ''}
              onChange={e => setEdited(prev => ({ ...prev, location: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-1 text-[12px] text-[color:var(--ink)]"
            />
          </label>
          <label className="block text-[11px] text-[color:var(--muted-ink)]">
            Urgency
            <select
              value={edited.urgency || 'standard'}
              onChange={e => setEdited(prev => ({ ...prev, urgency: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-1 text-[12px] text-[color:var(--ink)]"
            >
              <option value="standard">Standard</option>
              <option value="same_day">Same day</option>
              <option value="emergency">Emergency</option>
            </select>
          </label>
          <label className="block text-[11px] text-[color:var(--muted-ink)]">
            Tier
            <select
              value={edited.preferred_tier || 'standard'}
              onChange={e => setEdited(prev => ({ ...prev, preferred_tier: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-1 text-[12px] text-[color:var(--ink)]"
            >
              <option value="standard">Standard</option>
              <option value="budget">Budget</option>
              <option value="premium">Premium</option>
            </select>
          </label>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {chips.map(chip => (
            <span
              key={chip.key}
              className="inline-flex items-center gap-1 rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2.5 py-1 text-[11px] text-[color:var(--ink)]"
            >
              {chip.icon}
              <span className="font-medium">{chip.label}:</span> {chip.value}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={handleConfirm}
          className="inline-flex items-center gap-1 rounded-lg bg-[color:var(--accent)] px-3 py-1.5 text-[11px] font-medium text-white hover:bg-[color:var(--accent-hover)] transition-colors"
        >
          <Check size={12} />
          Looks right
        </button>
        <button
          type="button"
          onClick={() => { haptic('tap'); setIsEditing(v => !v) }}
          className="inline-flex items-center gap-1 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 text-[11px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] transition-colors"
        >
          <Pencil size={12} />
          {isEditing ? 'Done editing' : 'Edit'}
        </button>
      </div>
    </div>
  )
}
