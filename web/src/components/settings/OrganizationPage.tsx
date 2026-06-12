'use client'

import { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
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
import { formatDateMedium } from '@/lib/formatters'
import { useAnnouncer } from '@/components/layout/GlobalAnnouncer'
import {
  organizationSchema,
  inviteUserSchema,
  ROLE_OPTIONS,
  normalizeOrganizationValues,
  type OrganizationFormValues,
  type InviteUserFormValues,
} from '@/lib/forms/schemas'

const ROLE_BADGE_VARIANT: Record<string, 'accent' | 'info' | 'neutral'> = {
  admin: 'accent',
  estimator: 'info',
  viewer: 'neutral',
}

export function OrganizationPage() {
  const { user } = useAuth()
  const isAdmin = user?.is_admin ?? false
  const { announce } = useAnnouncer()

  const { data: org, isLoading: orgLoading, isError: orgError, refetch: refetchOrg } = useOrganization()
  const updateOrg = useUpdateOrganization()

  const { data: orgUsers, isLoading: usersLoading } = useOrgUsers()
  const inviteUser = useInviteUser()
  const updateRole = useUpdateUserRole()
  const removeUser = useRemoveUser()

  const [inviteOpen, setInviteOpen] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<OrgUser | null>(null)

  const orgForm = useForm<OrganizationFormValues>({
    resolver: zodResolver(organizationSchema),
    defaultValues: {
      name: '',
      address: '',
      phone: '',
      billingEmail: '',
      logoUrl: '',
      defaultTaxRate: undefined,
      defaultMarkupPercent: undefined,
    },
  })

  const inviteForm = useForm<InviteUserFormValues>({
    resolver: zodResolver(inviteUserSchema),
    defaultValues: { email: '', fullName: '', role: 'estimator' },
  })

  useEffect(() => {
    if (org) {
      orgForm.reset({
        name: org.name ?? '',
        address: org.address ?? '',
        phone: org.phone ?? '',
        billingEmail: org.billing_email ?? '',
        logoUrl: org.logo_url ?? '',
        defaultTaxRate: org.default_tax_rate != null ? String(org.default_tax_rate * 100) : '',
        defaultMarkupPercent: org.default_markup_percent != null ? String(org.default_markup_percent * 100) : '',
      })
    }
  }, [org, orgForm])

  const onSubmitOrg = (values: OrganizationFormValues) => {
    updateOrg.mutate(
      {
        ...normalizeOrganizationValues(values),
        billing_email: values.billingEmail || undefined,
        logo_url: values.logoUrl || undefined,
      },
      {
        onSuccess: () => announce('Organization details saved successfully'),
      },
    )
  }

  const onSubmitInvite = (values: InviteUserFormValues) => {
    inviteUser.mutate(
      { email: values.email, role: values.role, full_name: values.fullName?.trim() || undefined },
      {
        onSuccess: () => {
          setInviteOpen(false)
          inviteForm.reset()
          announce(`Invitation sent to ${values.email}`)
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
          {formatDateMedium(row.created_at ?? row.joined_at ?? '')}
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
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation()
                    setRemoveTarget(row)
                  }}
                  aria-label={`Remove ${row.full_name}`}
                >
                  <MoreHorizontal size={14} />
                </Button>
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
      <form onSubmit={orgForm.handleSubmit(onSubmitOrg)} noValidate>
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
              placeholder="Acme Plumbing LLC"
              disabled={!isAdmin}
              error={orgForm.formState.errors.name?.message}
              {...orgForm.register('name')}
            />
            <Input
              label="Phone"
              type="tel"
              placeholder="(555) 000-0000"
              disabled={!isAdmin}
              error={orgForm.formState.errors.phone?.message}
              {...orgForm.register('phone')}
            />
            <div className="sm:col-span-2">
              <Input
                label="Address"
                placeholder="123 Main St, Dallas, TX 75201"
                disabled={!isAdmin}
                error={orgForm.formState.errors.address?.message}
                {...orgForm.register('address')}
              />
            </div>
            <Input
              label="Billing Email"
              type="email"
              placeholder="billing@company.com"
              disabled={!isAdmin}
              error={orgForm.formState.errors.billingEmail?.message}
              {...orgForm.register('billingEmail')}
            />
            <Input
              label="Logo URL"
              type="url"
              placeholder="https://example.com/logo.png"
              disabled={!isAdmin}
              error={orgForm.formState.errors.logoUrl?.message}
              {...orgForm.register('logoUrl')}
            />
            <Input
              label="Default Tax Rate (%)"
              type="number"
              min={0}
              max={100}
              step={0.01}
              placeholder="8.25"
              helperText="Default tax rate applied to new estimates (e.g. 8.5 for 8.5%)"
              disabled={!isAdmin}
              error={orgForm.formState.errors.defaultTaxRate?.message}
              {...orgForm.register('defaultTaxRate')}
            />
            <Input
              label="Default Markup (%)"
              type="number"
              min={0}
              max={200}
              step={0.1}
              placeholder="20"
              helperText="Default markup applied to new estimates (e.g. 20 for 20%)"
              disabled={!isAdmin}
              error={orgForm.formState.errors.defaultMarkupPercent?.message}
              {...orgForm.register('defaultMarkupPercent')}
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
        <form onSubmit={inviteForm.handleSubmit(onSubmitInvite)} className="space-y-4" noValidate>
          <Input
            label="Email Address"
            type="email"
            placeholder="colleague@company.com"
            error={inviteForm.formState.errors.email?.message}
            {...inviteForm.register('email')}
          />
          <Input
            label="Full Name (optional)"
            placeholder="Jane Doe"
            error={inviteForm.formState.errors.fullName?.message}
            {...inviteForm.register('fullName')}
          />
          <Controller
            control={inviteForm.control}
            name="role"
            render={({ field }) => (
              <Select
                label="Role"
                options={ROLE_OPTIONS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
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
