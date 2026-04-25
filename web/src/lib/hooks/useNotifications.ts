import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notificationsApi, type BackendNotification } from '@/lib/api'
import type { AppNotification, NotificationType } from '@/lib/notifications'

export const notificationKeys = {
  all: ['notifications'] as const,
  unreadCount: ['notifications', 'unread-count'] as const,
}

const VALID_TYPES = new Set<NotificationType>([
  'blueprint_complete',
  'proposal_viewed',
  'proposal_accepted',
  'proposal_declined',
  'project_assigned',
  'job_failed',
  'invite_accepted',
  'price_alert',
  'outcome_recorded',
  'system',
])

function mapNotification(n: BackendNotification): AppNotification {
  const type = (VALID_TYPES.has(n.kind as NotificationType) ? n.kind : 'system') as NotificationType
  return {
    id: n.id,
    type,
    title: n.title,
    message: n.body ?? '',
    read: n.read_at !== null,
    createdAt: n.created_at,
    link: n.link ?? undefined,
  }
}

export function useNotifications() {
  return useQuery<AppNotification[]>({
    queryKey: notificationKeys.all,
    queryFn: async () => (await notificationsApi.list({ limit: 20 })).map(mapNotification),
    refetchInterval: 5 * 60_000,   // 5 min — notifications don't need sub-minute freshness
  })
}

export function useUnreadCount() {
  const { data } = useQuery<number>({
    queryKey: notificationKeys.unreadCount,
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 5 * 60_000,   // 5 min — badge updates on mark-read via mutation
    refetchOnWindowFocus: false,
  })
  return data ?? 0
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => notificationsApi.markRead([id]),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: notificationKeys.all })
      const previous = queryClient.getQueryData<AppNotification[]>(notificationKeys.all)
      queryClient.setQueryData<AppNotification[]>(notificationKeys.all, old =>
        old?.map(n => (n.id === id ? { ...n, read: true } : n)),
      )
      return { previous }
    },
    onError: (_err, _id, context) => {
      if (context?.previous) queryClient.setQueryData(notificationKeys.all, context.previous)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: notificationKeys.all })
      void queryClient.invalidateQueries({ queryKey: notificationKeys.unreadCount })
    },
  })
}

export function useMarkAllRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: notificationKeys.all })
      const previous = queryClient.getQueryData<AppNotification[]>(notificationKeys.all)
      queryClient.setQueryData<AppNotification[]>(notificationKeys.all, old =>
        old?.map(n => ({ ...n, read: true })),
      )
      queryClient.setQueryData<number>(notificationKeys.unreadCount, 0)
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(notificationKeys.all, context.previous)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: notificationKeys.all })
      void queryClient.invalidateQueries({ queryKey: notificationKeys.unreadCount })
    },
  })
}


export function useDismissNotification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => notificationsApi.delete(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: notificationKeys.all })
      const previous = queryClient.getQueryData<AppNotification[]>(notificationKeys.all)
      queryClient.setQueryData<AppNotification[]>(notificationKeys.all, old =>
        old?.filter(n => n.id !== id),
      )
      queryClient.setQueryData<number>(notificationKeys.unreadCount, old => Math.max(0, (old ?? 1) - 1))
      return { previous }
    },
    onError: (_err, _id, context) => {
      if (context?.previous) queryClient.setQueryData(notificationKeys.all, context.previous)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: notificationKeys.all })
      void queryClient.invalidateQueries({ queryKey: notificationKeys.unreadCount })
    },
  })
}
