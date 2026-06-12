'use client'

import { type ReactNode } from 'react'
import { ShieldAlert } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { Skeleton } from '@/components/ui/Skeleton'

interface AdminShellProps {
  children: ReactNode
}

function UnauthorizedAdmin() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center px-4">
      <div className="flex max-w-sm flex-col items-center gap-3 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[hsl(var(--danger)/0.1)] text-[hsl(var(--danger))]">
          <ShieldAlert size={24} />
        </div>
        <h1 className="text-lg font-semibold text-[color:var(--ink)]">Admin access required</h1>
        <p className="text-sm text-[color:var(--muted-ink)]">
          You don&apos;t have permission to view this area. Contact your organization admin if you
          think this is a mistake.
        </p>
      </div>
    </div>
  )
}

function AdminLoading() {
  return (
    <div className="mx-auto w-full max-w-[var(--content-max-width)] px-[var(--space-page-x)] py-[var(--space-page-y)]">
      <Skeleton variant="card" className="h-32 w-full rounded-2xl" />
      <div className="mt-6 space-y-4">
        <Skeleton variant="text" className="h-8 w-1/3 rounded-lg" />
        <Skeleton variant="text" className="h-4 w-1/2 rounded-md" />
        <Skeleton variant="card" className="h-64 w-full rounded-2xl" />
      </div>
    </div>
  )
}

/**
 * Client-side guard for admin-only routes. Wraps admin pages/layouts and shows
 * a loading skeleton while the session hydrates, then either renders children
 * or an unauthorized message.
 */
export function AdminShell({ children }: AdminShellProps) {
  const { user, loading } = useAuth()

  if (loading) return <AdminLoading />
  if (!user?.is_admin) return <UnauthorizedAdmin />

  return children
}
