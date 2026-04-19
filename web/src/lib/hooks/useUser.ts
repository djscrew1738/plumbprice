import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userApi, orgApi } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

// ─── Query keys ─────────────────────────────────────────────────────────────

export const userKeys = {
  all: ['user'] as const,
  profile: () => ['user', 'profile'] as const,
  org: () => ['user', 'org'] as const,
  orgUsers: () => ['user', 'org', 'users'] as const,
  orgInvites: () => ['user', 'org', 'invites'] as const,
}

// ─── Types ──────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: number
  email: string
  full_name: string
  phone?: string | null
  role: string
  is_admin: boolean
  avatar_url?: string | null
  created_at?: string
}

export interface Organization {
  id: number
  name: string
  address?: string | null
  phone?: string | null
  email?: string | null
  billing_email?: string | null
  logo_url?: string | null
  default_tax_rate?: number | null
  default_markup_percent?: number | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  license_number?: string | null
}

export interface OrgUser {
  id: string
  email: string
  full_name: string
  role: string
  is_active?: boolean
  is_admin?: boolean
  last_login_at?: string | null
  created_at?: string | null
  joined_at?: string
  avatar_url?: string | null
}

export interface OrgInvite {
  id: string
  email: string
  role: string
  full_name?: string | null
  expires_at: string
  created_at: string
}

// ─── Profile queries ────────────────────────────────────────────────────────

export function useProfile() {
  return useQuery({
    queryKey: userKeys.profile(),
    queryFn: () => userApi.getProfile() as Promise<UserProfile>,
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (data: { name?: string; email?: string; phone?: string }) =>
      userApi.updateProfile(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.profile() })
      toast.success('Profile updated')
    },
    onError: () => {
      toast.error('Failed to update profile')
    },
  })
}

export function useChangePassword() {
  const toast = useToast()

  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      userApi.changePassword(data),
    onSuccess: () => {
      toast.success('Password changed successfully')
    },
    onError: () => {
      toast.error('Failed to change password', 'Check your current password and try again.')
    },
  })
}

export function useUploadAvatar() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (file: File) => userApi.uploadAvatar(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.profile() })
      toast.success('Avatar updated')
    },
    onError: () => {
      toast.error('Failed to upload avatar')
    },
  })
}

// ─── Organization queries ───────────────────────────────────────────────────

export function useOrganization() {
  return useQuery({
    queryKey: userKeys.org(),
    queryFn: () => orgApi.get() as Promise<Organization>,
  })
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (data: {
      name?: string
      address?: string
      phone?: string
      logo_url?: string
      billing_email?: string
      default_tax_rate?: number
      default_markup_percent?: number
    }) => orgApi.update(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.org() })
      toast.success('Organization updated')
    },
    onError: () => {
      toast.error('Failed to update organization')
    },
  })
}

export function useUploadOrgLogo() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (file: File) => orgApi.uploadLogo(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.org() })
      toast.success('Logo uploaded')
    },
    onError: () => {
      toast.error('Failed to upload logo')
    },
  })
}

export function useOrgUsers() {
  return useQuery({
    queryKey: userKeys.orgUsers(),
    queryFn: () => orgApi.listUsers() as Promise<OrgUser[]>,
  })
}

export function useInviteUser() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (data: { email: string; role: string; full_name?: string }) =>
      orgApi.inviteUser(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.orgUsers() })
      void queryClient.invalidateQueries({ queryKey: userKeys.orgInvites() })
      toast.success('Invitation sent')
    },
    onError: () => {
      toast.error('Failed to send invitation')
    },
  })
}

export function useOrgInvites() {
  return useQuery({
    queryKey: userKeys.orgInvites(),
    queryFn: () => orgApi.listInvites() as Promise<OrgInvite[]>,
  })
}

export function useRevokeInvite() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (inviteId: string) => orgApi.revokeInvite(inviteId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.orgInvites() })
      toast.success('Invite revoked')
    },
    onError: () => {
      toast.error('Failed to revoke invite')
    },
  })
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      orgApi.updateUserRole(userId, role),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.orgUsers() })
      toast.success('Role updated')
    },
    onError: () => {
      toast.error('Failed to update role')
    },
  })
}

export function useRemoveUser() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (userId: string) => orgApi.removeUser(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.orgUsers() })
      toast.success('User removed')
    },
    onError: () => {
      toast.error('Failed to remove user')
    },
  })
}
