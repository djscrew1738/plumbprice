import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { api, suppliersApi } from '@/lib/api'

// ─── Query keys ─────────────────────────────────────────────────────────────

export const supplierKeys = {
  all: ['suppliers'] as const,
  catalog: (params?: { search?: string; category?: string }) =>
    ['suppliers', 'catalog', params ?? {}] as const,
  list: () => ['suppliers-list'] as const,
}

// ─── Types ──────────────────────────────────────────────────────────────────

export interface SupplierPrice { name: string; sku: string; cost: number }

export interface CatalogItem {
  canonical_id: string
  display_name: string
  category: string
  best_price: number
  best_supplier: string
  prices: { ferguson?: SupplierPrice; moore_supply?: SupplierPrice; apex?: SupplierPrice }
}

// ─── Queries ────────────────────────────────────────────────────────────────

export function useSuppliers(
  options?: Partial<UseQueryOptions<CatalogItem[]>>,
) {
  return useQuery({
    queryKey: supplierKeys.all,
    queryFn: async () => {
      const res = await api.get('/suppliers/catalog')
      const raw: Record<string, Record<string, { sku: string; name: string; cost: number }>> =
        res.data?.items ?? res.data ?? {}
      return Object.entries(raw).map(([canonical_id, prices]): CatalogItem => {
        const entries = Object.entries(prices) as [string, { sku: string; name: string; cost: number }][]
        let best_supplier = entries[0]?.[0] ?? ''
        let best_price    = entries[0]?.[1]?.cost ?? 0
        for (const [sup, p] of entries) {
          if (p.cost < best_price) { best_price = p.cost; best_supplier = sup }
        }
        return {
          canonical_id,
          display_name: canonical_id.replace(/\./g, ' › ').replace(/_/g, ' '),
          category: canonical_id.split('.')[0] ?? 'other',
          best_price,
          best_supplier,
          prices: prices as CatalogItem['prices'],
        }
      })
    },
    ...options,
  })
}

export function useSupplierCatalog(
  supplierId: string | undefined,
  params?: { search?: string; category?: string },
  options?: Partial<UseQueryOptions>,
) {
  return useQuery({
    queryKey: supplierKeys.catalog(params),
    queryFn: async () => {
      const res = await suppliersApi.catalog(params?.search)
      return res.data
    },
    enabled: !!supplierId,
    ...options,
  })
}

export function useSuppliersList(
  options?: Partial<UseQueryOptions>,
) {
  return useQuery({
    queryKey: supplierKeys.list(),
    queryFn: async () => {
      const res = await suppliersApi.list()
      return res.data
    },
    ...options,
  })
}
