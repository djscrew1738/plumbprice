import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { api, adminApi, type CanonicalItem } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

// ─── Query keys ─────────────────────────────────────────────────────────────

export const adminKeys = {
  all: ['admin'] as const,
  templates: () => ['admin', 'templates'] as const,
  markups: () => ['admin', 'markups'] as const,
  items: () => ['admin', 'items'] as const,
  stats: () => ['admin', 'stats'] as const,
}

// ─── Types ──────────────────────────────────────────────────────────────────

export interface LaborTemplate {
  code: string; name: string; category: string; base_hours: number
  lead_rate: number; helper_required: boolean; disposal_hours: number
}

interface MarkupRuleResponse {
  job_type: string; materials_markup_pct?: number; misc_flat?: number; misc_disposal_flat?: number
}

export interface MarkupRule {
  job_type: string; materials_markup_pct: number; misc_disposal_flat: number
}

export interface AdminStats {
  total_estimates: number; avg_estimate_value: number
  labor_templates_count: number; canonical_items_count: number
}

// ─── Queries ────────────────────────────────────────────────────────────────

export function useAdminTemplates(
  options?: Partial<UseQueryOptions<LaborTemplate[]>>,
) {
  return useQuery({
    queryKey: adminKeys.templates(),
    queryFn: async () => {
      const res = await api.get('/admin/labor-templates')
      return (res.data?.templates ?? res.data ?? []) as LaborTemplate[]
    },
    ...options,
  })
}

export function useAdminMarkups(
  options?: Partial<UseQueryOptions<MarkupRule[]>>,
) {
  return useQuery({
    queryKey: adminKeys.markups(),
    queryFn: async () => {
      const res = await api.get('/admin/markup-rules')
      return ((res.data ?? []) as MarkupRuleResponse[]).map(r => ({
        job_type: r.job_type,
        materials_markup_pct: Math.round((r.materials_markup_pct ?? 0) * 100),
        misc_disposal_flat: r.misc_flat ?? r.misc_disposal_flat ?? 0,
      }))
    },
    ...options,
  })
}

export function useAdminItems(
  options?: Partial<UseQueryOptions<CanonicalItem[]>>,
) {
  return useQuery({
    queryKey: adminKeys.items(),
    queryFn: async () => {
      const res = await adminApi.listCanonicalItems()
      return res.data?.items ?? []
    },
    ...options,
  })
}

export function useAdminStats(
  options?: Partial<UseQueryOptions<AdminStats>>,
) {
  return useQuery({
    queryKey: adminKeys.stats(),
    queryFn: async () => {
      const res = await api.get('/admin/stats')
      const d = res.data
      return {
        total_estimates: d.total_estimates ?? 0,
        avg_estimate_value: d.avg_estimate_value ?? 0,
        labor_templates_count: d.labor_templates_count ?? d.labor_templates ?? 0,
        canonical_items_count: d.canonical_items_count ?? d.canonical_items ?? 0,
      } as AdminStats
    },
    ...options,
  })
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useSaveMarkup() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: async (rules: MarkupRule[]) => {
      await Promise.all(rules.map(r =>
        api.put(`/admin/markup-rules/${r.job_type}`, {
          materials_markup_pct: r.materials_markup_pct / 100,
          misc_flat: r.misc_disposal_flat,
        })
      ))
    },
    onMutate: async (rules) => {
      await queryClient.cancelQueries({ queryKey: adminKeys.markups() })
      const previous = queryClient.getQueryData<MarkupRule[]>(adminKeys.markups())
      queryClient.setQueryData<MarkupRule[]>(adminKeys.markups(), (old) => {
        if (!old) return rules
        return old.map(existing => {
          const updated = rules.find(r => r.job_type === existing.job_type)
          return updated ?? existing
        })
      })
      return { previous }
    },
    onError: (_err, _rules, context) => {
      if (context?.previous) {
        queryClient.setQueryData(adminKeys.markups(), context.previous)
      }
      toast.error('Failed to save markup rules')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: adminKeys.markups() })
    },
  })
}

export function useSaveItem() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: async ({
      canonicalItem,
      updates,
    }: {
      canonicalItem: string
      updates: Array<{
        supplier: string
        name: string
        cost: number
        unit: string
        sku?: string
      }>
    }) => {
      await Promise.all(
        updates.map(u =>
          adminApi.updateCanonicalItem(canonicalItem, u.supplier, {
            name: u.name,
            cost: u.cost,
            unit: u.unit,
            sku: u.sku,
          })
        )
      )
    },
    onMutate: async ({ canonicalItem, updates }) => {
      await queryClient.cancelQueries({ queryKey: adminKeys.items() })
      const previous = queryClient.getQueryData<CanonicalItem[]>(adminKeys.items())
      queryClient.setQueryData<CanonicalItem[]>(adminKeys.items(), (old) => {
        if (!old) return old
        return old.map(item => {
          if (item.canonical_item !== canonicalItem) return item
          const newSuppliers = { ...item.suppliers }
          for (const u of updates) {
            if (newSuppliers[u.supplier]) {
              newSuppliers[u.supplier] = {
                ...newSuppliers[u.supplier],
                name: u.name,
                cost: u.cost,
                unit: u.unit,
                sku: u.sku ?? newSuppliers[u.supplier].sku,
              }
            }
          }
          return { ...item, suppliers: newSuppliers }
        })
      })
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(adminKeys.items(), context.previous)
      }
      toast.error('Failed to save item prices')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: adminKeys.items() })
    },
  })
}

export function useSaveTemplate() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: async (template: Record<string, unknown>) => {
      const res = await api.put(`/admin/labor-templates/${template.code}`, template)
      return res.data
    },
    onMutate: async (template) => {
      await queryClient.cancelQueries({ queryKey: adminKeys.templates() })
      const previous = queryClient.getQueryData<LaborTemplate[]>(adminKeys.templates())
      queryClient.setQueryData<LaborTemplate[]>(adminKeys.templates(), (old) => {
        if (!old) return old
        return old.map(t =>
          t.code === template.code ? { ...t, ...template } as LaborTemplate : t,
        )
      })
      return { previous }
    },
    onError: (_err, _template, context) => {
      if (context?.previous) {
        queryClient.setQueryData(adminKeys.templates(), context.previous)
      }
      toast.error('Failed to save template')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: adminKeys.templates() })
    },
  })
}
