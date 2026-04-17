'use client'

import { useState, useEffect } from 'react'
import { User, Lock, Camera } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Avatar } from '@/components/ui/Avatar'
import { useProfile, useUpdateProfile, useChangePassword } from '@/lib/hooks'

export function ProfilePage() {
  const { data: profile, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()
  const changePassword = useChangePassword()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')

  useEffect(() => {
    if (profile) {
      setName(profile.full_name ?? '')
      setEmail(profile.email ?? '')
      setPhone(profile.phone ?? '')
    }
  }, [profile])

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault()
    updateProfile.mutate({ name, email, phone })
  }

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError('')

    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }

    changePassword.mutate(
      { current_password: currentPassword, new_password: newPassword },
      {
        onSuccess: () => {
          setCurrentPassword('')
          setNewPassword('')
          setConfirmPassword('')
        },
      },
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6 animate-pulse"
          >
            <div className="h-6 w-40 rounded bg-[color:var(--panel-strong)]" />
            <div className="mt-4 space-y-3">
              <div className="h-10 rounded-xl bg-[color:var(--panel-strong)]" />
              <div className="h-10 rounded-xl bg-[color:var(--panel-strong)]" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Profile Information */}
      <form onSubmit={handleSaveProfile}>
        <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
          <div className="flex items-center gap-3 mb-6">
            <User size={18} className="text-[color:var(--accent-strong)]" aria-hidden="true" />
            <h2 className="text-base font-semibold text-[color:var(--ink)]">
              Profile Information
            </h2>
          </div>

          {/* Avatar section */}
          <div className="flex items-center gap-4 mb-6 pb-6 border-b border-[color:var(--line)]">
            <div className="relative">
              <Avatar
                src={profile?.avatar_url ?? undefined}
                alt={profile?.full_name ?? ''}
                fallback={profile?.full_name?.charAt(0)?.toUpperCase()}
                size="xl"
              />
              <button
                type="button"
                className="absolute -bottom-1 -right-1 rounded-full bg-[color:var(--accent)] p-1.5 text-white shadow-md hover:bg-[color:var(--accent-strong)] transition-colors"
                aria-label="Change avatar"
              >
                <Camera size={12} />
              </button>
            </div>
            <div>
              <p className="text-sm font-semibold text-[color:var(--ink)]">
                {profile?.full_name}
              </p>
              <p className="text-xs text-[color:var(--muted-ink)]">{profile?.email}</p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
            />
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
            <Input
              label="Phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="(555) 123-4567"
            />
          </div>

          <div className="mt-6 flex justify-end">
            <Button type="submit" isLoading={updateProfile.isPending}>
              Save Changes
            </Button>
          </div>
        </div>
      </form>

      {/* Change Password */}
      <form onSubmit={handleChangePassword}>
        <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
          <div className="flex items-center gap-3 mb-6">
            <Lock size={18} className="text-[color:var(--accent-strong)]" aria-hidden="true" />
            <h2 className="text-base font-semibold text-[color:var(--ink)]">
              Change Password
            </h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Input
                label="Current Password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
              />
            </div>
            <Input
              label="New Password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter new password"
              helperText="Minimum 8 characters"
            />
            <Input
              label="Confirm New Password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm new password"
              error={passwordError || undefined}
            />
          </div>

          <div className="mt-6 flex justify-end">
            <Button
              type="submit"
              variant="secondary"
              isLoading={changePassword.isPending}
              disabled={!currentPassword || !newPassword || !confirmPassword}
            >
              Update Password
            </Button>
          </div>
        </div>
      </form>
    </div>
  )
}
