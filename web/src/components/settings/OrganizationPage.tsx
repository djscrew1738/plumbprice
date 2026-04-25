'use client'

import { useState, useEffect } from 'react'
import { Building2, Users, UserPlus, MoreHorizontal, ShieldCheck } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Avatar } from '@/components/ui/Avatar'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { useAuth } from '@/contexts/AuthContext'
import {
  useOrganization,
  useUpdateOrganization,
  useOrgUsers,
  useInviteUser,
  useUpdateUserRole,
  useRemoveUser,
  type OrgUser,
} from '@/lib/hooks'
import { ErrorState } from '@/components/ui/ErrorState'

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Admin' },
  { value: 'estimator', label: 'Estimator' },
  { value: 'viewer', label: 'Viewer' },
]

const ROLE_BADGE_VARIANT: Record<string, 'accent' | 'info' | 'neutral'> = {
  admin: 'accent',
  estimator: 'info',
  viewer: 'neutral',
}

function formatDate(dateStr: string) {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(dateStr))
  } catch {
    return dateStr
  }
}

export function OrganizationPage() {
  const { user } = useAuth()
  const isAdmin = user?.is_admin ?? false

  const { data: org, isLoading: orgLoading, isError: orgError, refetch: refetchOrg } = useOrganization()
  const updateOrg = useUpdateOrganization()

  const { data: orgUsers, isLoading: usersLoading } = useOrgUsers()
  const inviteUser = useInviteUser()
  const updateRole = useUpdateUserRole()
  const removeUser = useRemoveUser()

  const [orgName, setOrgName] = useState('')
  const [orgAddress, setOrgAddress] = useState('')
  const [orgPhone, setOrgPhone] = useState('')
  const [billingEmail, setBillingEmail] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [defaultTaxRate, setDefaultTaxRate] = useState('')
  const [defaultMarkupPercent, setDefaultMarkupPercent] = useState('')

  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('estimator')

  const [removeTarget, setRemoveTarget] = useState<OrgUser | null>(null)

  useEffect(() => {
    if (org) {
      setOrgName(org.name ?? '')
      setOrgAddress(org.address ?? '')
      setOrgPhone(org.phone ?? '')
      setBillingEmail(org.billing_email ?? '')
      setLogoUrl(org.logo_url ?? '')
      setDefaultTaxRate(org.default_tax_rate != null ? String(org.default_tax_rate * 100) : '')
      setDefaultMarkupPercent(org.default_markup_percent != null ? String(org.default_markup_percent * 100) : '')
    }
  }, [org])

  const handleSaveOrg = (e: React.FormEvent) => {
    e.preventDefault()
    updateOrg.mutate({
      name: orgName,
      address: orgAddress,
      phone: orgPhone,
      billing_email: billingEmail || undefined,
      logo_url: logoUrl || undefined,
      default_tax_rate: defaultTaxRate !== '' ? parseFloat(defaultTaxRate) / 100 : undefined,
      default_markup_percent: defaultMarkupPercent !== '' ? parseFloat(defaultMarkupPercent) / 100 : undefined,
    })
  }

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault()
    inviteUser.mutate(
      { email: inviteEmail, role: inviteRole },
      {
        onSuccess: () => {
          setInviteOpen(false)
          setInviteEmail('')
          setInviteRole('estimator')
        },
      },
    )
  }

  const handleRemove = () => {
    if (!removeTarget) return
    removeUser.mutate(removeTarget.id, {
      onSuccess: () => setRemoveTarget(null),
    })
  }

  const columns: Column<OrgUser>[] = [
    {
      key: 'user',
      header: 'User',
      render: (row) => (
        <div className="flex items-center gap-3">
          <Avatar
            src={row.avatar_url ?? undefined}
            alt={row.full_name}
            fallback={row.full_name?.charAt(0)?.toUpperCase()}
            size="sm"
          />
          <div className="min-w-0">
            <p className="text-sm font-medium text-[color:var(--ink)] truncate">
              {row.full_name}
            </p>
            <p className="text-xs text-[color:var(--muted-ink)] truncate">
              {row.email}
            </p>
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      width: '160px',
      render: (row) =>
        isAdmin && row.id !== String(user?.id) ? (
          <Select
            options={ROLE_OPTIONS}
            value={row.role}
            onChange={(val) =>
              updateRole.mutate({ userId: row.id, role: val })
            }
            size="sm"
          />
        ) : (
          <Badge variant={ROLE_BADGE_VARIANT[row.role] ?? 'neutral'} size="sm">
            {row.role}
          </Badge>
        ),
    },
    {
      key: 'joined_at',
      header: 'Joined',
      width: '120px',
      render: (row) => (
        <span className="text-xs text-[color:var(--muted-ink)]">
          {formatDate(row.created_at ?? row.joined_at ?? '')}
        </span>
      ),
    },
    ...(isAdmin
      ? [
          {
            key: 'actions',
            header: '',
            width: '48px',
            align: 'center' as const,
            render: (row: OrgUser) =>
              row.id !== String(user?.id) ? (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setRemoveTarget(row)
                  }}
                  className="rounded-lg p-1.5 text-[color:var(--muted-ink)] hover:text-[hsl(var(--danger))] hover:bg-[hsl(var(--danger)/0.1)] transition-colors"
                  aria-label={`Remove ${row.full_name}`}
                >
                  <MoreHorizontal size={14} />
                </button>
              ) : null,
          },
        ]
      : []),
  ]

  if (orgLoading) {
    return (
      <div className="space-y-6">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6 animate-pulse"
          >
            <div className="h-6 w-48 rounded bg-[color:var(--panel-strong)]" />
            <div className="mt-4 space-y-3">
              <div className="h-10 rounded-xl bg-[color:var(--panel-strong)]" />
              <div className="h-10 rounded-xl bg-[color:var(--panel-strong)]" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (orgError) {
    return <ErrorState message="Failed to load organization" onRetry={() => void refetchOrg()} />
  }

  return (
    <div className="space-y-6">
      {/* Organization Info */}
      <form onSubmit={handleSaveOrg}>
        <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
          <div className="flex items-center gap-3 mb-6">
            <Building2 size={18} className="text-[color:var(--accent-strong)]" aria-hidden="true" />
            <h2 className="text-base font-semibold text-[color:var(--ink)]">
              Organization Details
            </h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Organization Name"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Acme Plumbing LLC"
              disabled={!isAdmin}
            />
            <Input
              label="Phone"
              type="tel"
              value={orgPhone}
              onChange={(e) => setOrgPhone(e.target.value)}
              placeholder="(555) 000-0000"
              disabled={!isAdmin}
            />
            <div className="sm:col-span-2">
              <Input
                label="Address"
                value={orgAddress}
                onChange={(e) => setOrgAddress(e.target.value)}
                placeholder="123 Main St, Dallas, TX 75201"
                disabled={!isAdmin}
              />
            </div>
            <Input
              label="Billing Email"
              type="email"
              value={billingEmail}
              onChange={(e) => setBillingEmail(e.target.value)}
              placeholder="billing@company.com"
              disabled={!isAdmin}
            />
            <Input
              label="Logo URL"
              type="url"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              placeholder="https://example.com/logo.png"
              disabled={!isAdmin}
            />
            <Input
              label="Default Tax Rate (%)"
              type="number"
              min={0}
              max={100}
              step={0.01}
              value={defaultTaxRate}
              onChange={(e) => setDefaultTaxRate(e.target.value)}
              placeholder="8.25"
              helperText="Default tax rate applied to new estimates (e.g. 8.5 for 8.5%)"
              disabled={!isAdmin}
            />
            <Input
              label="Default Markup (%)"
              type="number"
              min={0}
              max={200}
              step={0.1}
              value={defaultMarkupPercent}
              onChange={(e) => setDefaultMarkupPercent(e.target.value)}
              placeholder="20"
              helperText="Default markup applied to new estimates (e.g. 20 for 20%)"
              disabled={!isAdmin}
            />
          </div>

          {isAdmin && (
            <div className="mt-6 flex justify-end">
              <Button type="submit" isLoading={updateOrg.isPending}>
                Save Changes
              </Button>
            </div>
          )}
        </div>
      </form>

      {/* Team Members */}
      <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Users size={18} className="text-[color:var(--accent-strong)]" aria-hidden="true" />
            <h2 className="text-base font-semibold text-[color:var(--ink)]">
              Team Members
            </h2>
            {orgUsers && (
              <Badge variant="neutral" size="sm">
                {orgUsers.length}
              </Badge>
            )}
          </div>

          {isAdmin && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setInviteOpen(true)}
            >
              <UserPlus size={14} />
              Invite
            </Button>
          )}
        </div>

        <DataTable
          columns={columns}
          data={orgUsers ?? []}
          keyExtractor={(row) => row.id}
          loading={usersLoading}
          emptyMessage="No team members found"
        />

        {!isAdmin && (
          <div className="mt-4 flex items-center gap-2 rounded-xl bg-[color:var(--panel-strong)] px-4 py-3">
            <ShieldCheck size={14} className="text-[color:var(--muted-ink)] shrink-0" aria-hidden="true" />
            <p className="text-xs text-[color:var(--muted-ink)]">
              Contact an admin to manage team members and roles.
            </p>
          </div>
        )}
      </div>

      {/* Invite Modal */}
      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Invite Team Member"
        description="Send an invitation to join your organization."
        size="sm"
      >
        <form onSubmit={handleInvite} className="space-y-4">
          <Input
            label="Email Address"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="colleague@company.com"
            required
          />
          <Select
            label="Role"
            options={ROLE_OPTIONS}
            value={inviteRole}
            onChange={setInviteRole}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setInviteOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={inviteUser.isPending}
              disabled={!inviteEmail}
            >
              Send Invite
            </Button>
          </div>
        </form>
      </Modal>

      {/* Remove Confirmation */}
      <ConfirmDialog
        open={!!removeTarget}
        onClose={() => setRemoveTarget(null)}
        onConfirm={handleRemove}
        title="Remove Team Member"
        description={`Are you sure you want to remove ${removeTarget?.full_name ?? 'this user'}? They will lose access to the organization.`}
        confirmLabel="Remove"
        variant="danger"
        isLoading={removeUser.isPending}
      />
    </div>
  )
}
