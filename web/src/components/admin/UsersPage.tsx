'use client'

import { useState } from 'react'
import { UserPlus, ShieldCheck } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { useAuth } from '@/contexts/AuthContext'
import {
  useOrgUsers,
  useOrgInvites,
  useInviteUser,
  useUpdateUserRole,
  useRemoveUser,
  useRevokeInvite,
  type OrgUser,
  type OrgInvite,
} from '@/lib/hooks'

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

function formatDate(dateStr?: string | null) {
  if (!dateStr) return '—'
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

export function AdminUsersPage() {
  const { user } = useAuth()
  const isAdmin = user?.is_admin ?? false

  const { data: orgUsers, isLoading: usersLoading } = useOrgUsers()
  const { data: pendingInvites } = useOrgInvites()
  const inviteUser = useInviteUser()
  const updateRole = useUpdateUserRole()
  const removeUser = useRemoveUser()
  const revokeInvite = useRevokeInvite()

  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('estimator')
  const [inviteName, setInviteName] = useState('')
  const [removeTarget, setRemoveTarget] = useState<OrgUser | null>(null)

  if (!isAdmin) {
    return (
      <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-[color:var(--muted-ink)]" />
          <p className="text-sm text-[color:var(--muted-ink)]">
            You must be an admin to manage users.
          </p>
        </div>
      </div>
    )
  }

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault()
    inviteUser.mutate(
      { email: inviteEmail, role: inviteRole, full_name: inviteName || undefined },
      {
        onSuccess: () => {
          setInviteOpen(false)
          setInviteEmail('')
          setInviteName('')
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
      key: 'email',
      header: 'Email',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-[color:var(--ink)]">
            {row.email}
          </p>
          {row.full_name && (
            <p className="truncate text-xs text-[color:var(--muted-ink)]">
              {row.full_name}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (row) =>
        row.id !== String(user?.id) ? (
          <Select
            options={ROLE_OPTIONS}
            value={row.role}
            onChange={(val) => updateRole.mutate({ userId: row.id, role: val })}
            size="sm"
          />
        ) : (
          <Badge variant={ROLE_BADGE_VARIANT[row.role] ?? 'neutral'} size="sm">
            {row.role}
          </Badge>
        ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) => (
        <Badge variant={row.is_active ? 'info' : 'neutral'} size="sm">
          {row.is_active ? 'Active' : 'Disabled'}
        </Badge>
      ),
    },
    {
      key: 'last_login_at',
      header: 'Last Login',
      className: 'hidden sm:table-cell',
      render: (row) => (
        <span className="text-xs text-[color:var(--muted-ink)]">
          {formatDate(row.last_login_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) =>
        row.id !== String(user?.id) && row.is_active ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setRemoveTarget(row)}
          >
            Deactivate
          </Button>
        ) : null,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-[color:var(--ink)]">
            Team Members
          </h2>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => setInviteOpen(true)}
          >
            <UserPlus size={14} />
            Invite user
          </Button>
        </div>
        <DataTable
          columns={columns}
          data={orgUsers ?? []}
          keyExtractor={(row) => row.id}
          loading={usersLoading}
          emptyMessage="No users yet"
        />
      </div>

      {pendingInvites && pendingInvites.length > 0 && (
        <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
          <h2 className="mb-4 text-base font-semibold text-[color:var(--ink)]">
            Pending Invites
          </h2>
          <ul className="divide-y divide-[color:var(--line)]">
            {pendingInvites.map((inv: OrgInvite) => (
              <li key={inv.id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[color:var(--ink)]">
                    {inv.email}
                  </p>
                  <p className="text-xs text-[color:var(--muted-ink)]">
                    {inv.role} · expires {formatDate(inv.expires_at)}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => revokeInvite.mutate(inv.id)}
                  isLoading={revokeInvite.isPending}
                  disabled={revokeInvite.isPending}
                >
                  Revoke
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Invite a user"
        description="Send an email invitation to join your organization."
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
          <Input
            label="Full Name (optional)"
            value={inviteName}
            onChange={(e) => setInviteName(e.target.value)}
            placeholder="Jane Doe"
          />
          <Select
            label="Role"
            options={ROLE_OPTIONS}
            value={inviteRole}
            onChange={setInviteRole}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => setInviteOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={inviteUser.isPending} disabled={!inviteEmail}>
              Send Invite
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!removeTarget}
        onClose={() => setRemoveTarget(null)}
        onConfirm={handleRemove}
        title="Deactivate user"
        description={`Are you sure you want to deactivate ${
          removeTarget?.full_name || removeTarget?.email || 'this user'
        }? They will lose access to the organization.`}
        confirmLabel="Deactivate"
        variant="danger"
        isLoading={removeUser.isPending}
      />
    </div>
  )
}
