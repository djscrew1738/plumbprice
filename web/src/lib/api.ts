import axios from 'axios'
import type { ProjectPipelineResponse, ProjectPipelineItem } from '@/types'

export type { ProjectPipelineItem, ProjectPipelineResponse }

// ─── Axios instance ───────────────────────────────────────────────────────────
// In the browser we use relative paths so Next.js rewrites handle the proxy.
// In SSR/build contexts we use the explicit env var.

const BASE_URL = typeof window === 'undefined'
  ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  : ''

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ─── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatPriceRequest {
  message: string
  county?: string
  preferred_supplier?: string
  job_type?: string
}

export interface ChatPriceResponse {
  answer: string
  estimate: EstimateBreakdownPayload | null
  estimate_id?: number | null
  confidence: number
  confidence_label: string
  assumptions: string[]
  sources: string[]
  job_type_detected?: string | null
  template_used?: string | null
  classified_by?: 'keyword' | 'llm' | null
}

export interface EstimateBreakdownPayload {
  labor_total: number
  materials_total: number
  tax_total: number
  markup_total: number
  misc_total: number
  subtotal: number
  grand_total: number
  line_items: LineItemPayload[]
}

export interface LineItemPayload {
  line_type: string
  description: string
  quantity: number
  unit: string
  unit_cost: number
  total_cost: number
  supplier?: string | null
  sku?: string | null
  canonical_item?: string | null
  trace_json?: Record<string, unknown> | null
}

export const chatApi = {
  price: (body: ChatPriceRequest) =>
    api.post<ChatPriceResponse>('/chat/price', body),
}

// ─── Estimates ────────────────────────────────────────────────────────────────

export interface EstimateListItem {
  id: number
  title: string
  job_type: string
  status: string
  grand_total: number
  confidence_label: string
  county: string
  created_at: string
}

export const estimatesApi = {
  list: (params?: { job_type?: string; status?: string; limit?: number; offset?: number }) =>
    api.get<EstimateListItem[]>('/estimates', { params }),
  get: (id: number) =>
    api.get(`/estimates/${id}`),
  updateStatus: (id: number, status: string) =>
    api.patch<{ id: number; status: string }>(`/estimates/${id}/status`, { status }),
  delete: (id: number) =>
    api.delete(`/estimates/${id}`),
}

// ─── Projects / Pipeline ──────────────────────────────────────────────────────

export const projectsApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) =>
    api.get<ProjectPipelineResponse>('/projects', { params }),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (body: {
    name: string
    job_type: string
    customer_name?: string
    county?: string
    city?: string
    state?: string
    zip_code?: string
    notes?: string
  }) => api.post<ProjectPipelineResponse>('/projects', body),
  update: (id: number, body: {
    status?: string
    customer_name?: string
    customer_phone?: string
    customer_email?: string
    notes?: string
    city?: string
    county?: string
  }) => api.patch(`/projects/${id}`, body),
  delete: (id: number) => api.delete(`/projects/${id}`),
}

// ─── Suppliers ────────────────────────────────────────────────────────────────

export const suppliersApi = {
  catalog: (search?: string) =>
    api.get('/suppliers/catalog', { params: search ? { search } : undefined }),
  compare: (items: string[]) =>
    api.post('/suppliers/compare', { items }),
  list: () => api.get('/suppliers'),
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export const adminApi = {
  listTemplates: () =>
    api.get('/admin/labor-templates'),
  getMarkupRules: () =>
    api.get('/admin/markup-rules'),
  updateMarkupRule: (job_type: string, body: { materials_markup_pct: number; misc_flat: number }) =>
    api.put(`/admin/markup-rules/${job_type}`, body),
  getStats: () =>
    api.get('/admin/stats'),
  listAssemblies: () =>
    api.get('/admin/assemblies'),
}
