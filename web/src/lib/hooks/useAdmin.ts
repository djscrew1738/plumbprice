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

// ─── Bulk Import ─────────────────────────────────────────────────────────────

export interface BulkImportResult {
  dry_run: boolean
  total_rows: number
  created: number
  updated: number
  skipped: number
  errors: number
  rows: Array<{
    row_number: number
    status: string
    canonical_item?: string | null
    code?: string | null
    message: string
    details?: Record<string, unknown>
  }>
}

export function useBulkImportProducts() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: async ({ file, dryRun }: { file: File; dryRun: boolean }) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post(`/admin/pricing/bulk-import/products?dry_run=${dryRun}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data as BulkImportResult
    },
    onSuccess: (data) => {
      if (!data.dry_run) {
        void queryClient.invalidateQueries({ queryKey: adminKeys.items() })
        toast.success(`Import complete: ${data.created} created, ${data.updated} updated`)
      }
    },
    onError: () => toast.error('Import failed'),
  })
}

export function useAdminCatalog(
  search?: string,
  category?: string,
  supplier?: string,
  options?: Partial<UseQueryOptions<AdminCatalogItem[]>>,
) {
  return useQuery({
    queryKey: ['admin', 'catalog', search, category, supplier],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (search) params.append('search', search)
      if (category) params.append('category', category)
      if (supplier) params.append('supplier', supplier)
      const res = await api.get(`/admin/pricing/catalog?${params.toString()}`)
      return (res.data?.items ?? []) as AdminCatalogItem[]
    },
    ...options,
  })
}

export interface AdminCatalogItem {
  id: number
  canonical_item: string
  name: string
  sku: string | null
  supplier: string
  cost: number
  msrp: number | null
  manufacturer: string | null
  category: string | null
  sub_category: string | null
  in_stock: boolean
  lead_time: string | null
  tags: string[] | null
  confidence_score: number
  last_verified: string | null
}

export function useAdminFeedHealth(
  options?: Partial<UseQueryOptions<FeedHealthItem[]>>,
) {
  return useQuery({
    queryKey: ['admin', 'feed-health'],
    queryFn: async () => {
      const res = await api.get('/admin/pricing/feeds/health')
      return (res.data?.feeds ?? []) as FeedHealthItem[]
    },
    refetchInterval: 30000,
    ...options,
  })
}

export interface FeedHealthItem {
  name: string
  status: string
  last_sync: string | null
  items_synced: number
  error_count: number
  error_message: string | null
  response_time_ms: number | null
}

export interface PriceAlertItem {
  id: number
  product_id: number
  canonical_item: string
  product_name: string
  supplier_name: string
  old_cost: number
  new_cost: number
  pct_change: number
  source: string
  recorded_at: string
}

export interface PriceAlertResponse {
  alerts: PriceAlertItem[]
  total: number
  threshold_pct: number
}

export function useAdminPriceAlerts(
  days: number = 7,
  thresholdPct: number = 10,
  options?: Partial<UseQueryOptions<PriceAlertResponse>>,
) {
  return useQuery({
    queryKey: ['admin', 'price-alerts', days, thresholdPct],
    queryFn: async () => {
      const res = await api.get('/admin/price-alerts', {
        params: { days, threshold_pct: thresholdPct },
      })
      return (res.data ?? { alerts: [], total: 0, threshold_pct: thresholdPct }) as PriceAlertResponse
    },
    ...options,
  })
}

export function useBulkImportLabor() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: async ({ file, dryRun }: { file: File; dryRun: boolean }) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post(`/admin/pricing/bulk-import/labor?dry_run=${dryRun}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data as BulkImportResult
    },
    onSuccess: (data) => {
      if (!data.dry_run) {
        void queryClient.invalidateQueries({ queryKey: adminKeys.templates() })
        toast.success(`Import complete: ${data.created} created, ${data.updated} updated`)
      }
    },
    onError: () => toast.error('Import failed'),
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
