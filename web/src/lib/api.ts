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

// Attach stored JWT on every request
api.interceptors.request.use(config => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('pp_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// On 401, clear session and redirect to login
api.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('pp_token')
      localStorage.removeItem('pp_user')
      document.cookie = 'pp_token=; path=/; max-age=0'
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// ─── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatPriceRequest {
  message: string
  county?: string
  preferred_supplier?: string
  job_type?: string
  conversation_id?: string
  session_id?: number | null
  history?: ChatHistoryMessage[]
}

export interface ChatPriceStreamEvent {
  type: 'pricing' | 'token' | 'done'
  // pricing event payload
  estimate?: EstimateBreakdownPayload | null
  estimate_id?: number | null
  session_id?: number | null
  confidence?: number
  confidence_label?: string
  assumptions?: string[]
  sources?: string[]
  conversation_id?: string | null
  job_type_detected?: string | null
  template_used?: string | null
  classified_by?: 'keyword' | 'llm' | null
  // token event payload
  token?: string
}

export interface ChatPriceResponse {
  answer: string
  estimate: EstimateBreakdownPayload | null
  estimate_id?: number | null
  session_id?: number | null
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

  /** SSE stream — yields parsed ChatPriceStreamEvents until done */
  async *priceStream(body: ChatPriceRequest): AsyncGenerator<ChatPriceStreamEvent> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('pp_token') : null
    const base = typeof window === 'undefined'
      ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
      : ''
    const res = await fetch(`${base}/api/v1/chat/price/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok || !res.body) {
      throw new Error(`Stream request failed: ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    let currentEvent = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const raw = line.slice(6).trim()
          try {
            const payload = JSON.parse(raw) as Record<string, unknown>
            if (currentEvent === 'pricing') {
              yield { type: 'pricing', ...(payload as Omit<ChatPriceStreamEvent, 'type'>) }
            } else if (currentEvent === 'token') {
              yield { type: 'token', token: raw.replace(/^"|"$/g, '').replace(/\\"/g, '"') }
            } else if (currentEvent === 'done') {
              yield { type: 'done' }
              return
            }
          } catch { /* skip malformed lines */ }
        }
      }
    }
  },
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

export interface EstimateDetailResponse {
  id: number
  title: string
  status: string
  job_type: string
  county: string
  confidence_score: number
  confidence_label: string
  assumptions: string[]
  labor_total: number
  materials_total: number
  tax_total: number
  markup_total: number
  misc_total: number
  subtotal: number
  grand_total: number
  line_items: Array<{
    line_type: string
    description: string
    quantity: number
    unit: string
    unit_cost: number
    total_cost: number
    supplier?: string | null
    sku?: string | null
  }>
  created_at: string
}

export type EstimatesListResponse = EstimateListItem[] | { estimates?: EstimateListItem[] }

export const estimatesApi = {
  list: (params?: { job_type?: string; status?: string; limit?: number; offset?: number }) =>
    api.get<EstimateListItem[]>('/estimates', { params }),
  get: (id: number) =>
    api.get<EstimateDetailResponse>(`/estimates/${id}`),
  createService: (body: Record<string, unknown>) =>
    api.post('/estimates/service', body),
  createConstruction: (body: Record<string, unknown>) =>
    api.post('/estimates/construction', body),
  updateStatus: (id: number, status: string) =>
    api.patch<{ id: number; status: string }>(`/estimates/${id}/status`, { status }),
  delete: (id: number) =>
    api.delete(`/estimates/${id}`),
  duplicate: (id: number) =>
    api.post(`/estimates/${id}/duplicate`, {}),
  getCostBreakdown: (id: number) =>
    api.get(`/estimates/${id}/cost-breakdown`),
  getVersions: (id: number) =>
    api.get(`/estimates/${id}/versions`),
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
  updateProduct: (productId: number, body: Record<string, unknown>) =>
    api.put(`/suppliers/products/${productId}`, body),
  updatePrices: (supplierId: number, body: Record<string, unknown>) =>
    api.post(`/suppliers/${supplierId}/prices`, body),
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export interface CanonicalItemSupplier {
  id: number
  sku?: string | null
  name: string
  cost: number
  unit: string
  confidence_score?: number
  last_verified?: string | null
}

export interface CanonicalItem {
  canonical_item: string
  suppliers: Record<string, CanonicalItemSupplier>
}

export interface CanonicalItemsResponse {
  count: number
  items: CanonicalItem[]
}

export const adminApi = {
  listTemplates: () =>
    api.get('/admin/labor-templates'),
  getTemplate: (code: string) =>
    api.get(`/admin/labor-templates/${code}`),
  getMarkupRules: () =>
    api.get('/admin/markup-rules'),
  updateMarkupRule: (job_type: string, body: { materials_markup_pct: number; misc_flat: number }) =>
    api.put(`/admin/markup-rules/${job_type}`, body),
  getStats: () =>
    api.get('/admin/stats'),
  listAssemblies: () =>
    api.get('/admin/assemblies'),
  listCanonicalItems: () =>
    api.get<CanonicalItemsResponse>('/admin/canonical-items'),
  updateCanonicalItem: (
    item: string,
    supplier: string,
    body: { name: string; cost: number; unit: string; sku?: string },
  ) => api.put(`/admin/canonical-items/${encodeURIComponent(item)}/${supplier}`, body),
}

// ─── Blueprints ─────────────────────────────────────────────────────────────

export const blueprintsApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/blueprints/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
    })
  },
  getStatus: (jobId: string) =>
    api.get(`/blueprints/${jobId}/status`),
  getTakeoff: (jobId: string) =>
    api.get(`/blueprints/${jobId}/takeoff`),
}

// ─── Proposals ──────────────────────────────────────────────────────────────

export interface SendProposalRequest {
  recipient_email: string
  recipient_name?: string
  message?: string
}

export interface SendProposalResponse {
  success: boolean
  proposal_id: number
  sent: boolean
  recipient: string
}

export const proposalsApi = {
  send: (estimateId: number, body: SendProposalRequest) =>
    api.post<SendProposalResponse>(`/proposals/${estimateId}/send`, body),
  listSends: (estimateId: number) =>
    api.get<Array<{ id: number; recipient_email: string; recipient_name: string | null; sent_at: string | null; created_at: string }>>(`/proposals/${estimateId}/sends`),
}

// ─── Sessions ────────────────────────────────────────────────────────────────

export interface ChatSessionSummary {
  id: number
  title: string | null
  county: string | null
  created_at: string
  updated_at: string
}

export interface ChatSessionDetail extends ChatSessionSummary {
  messages: Array<{
    id: number
    role: 'user' | 'assistant'
    content: string
    estimate_id: number | null
    created_at: string
  }>
}

export const sessionsApi = {
  list: (limit = 20) =>
    api.get<ChatSessionSummary[]>('/sessions/', { params: { limit } }),
  get: (id: number) =>
    api.get<ChatSessionDetail>(`/sessions/${id}`),
  delete: (id: number) =>
    api.delete(`/sessions/${id}`),
}

// ─── Outcomes ────────────────────────────────────────────────────────────────

export type OutcomeValue = 'won' | 'lost' | 'pending' | 'no_bid'

export interface RecordOutcomeRequest {
  outcome: OutcomeValue
  final_price?: number
  notes?: string
}

export interface OutcomeResponse {
  id: number
  estimate_id: number
  outcome: OutcomeValue
  final_price: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface OutcomeStats {
  total: number
  won: number
  lost: number
  pending: number
  no_bid: number
  win_rate: number | null
  confidence_breakdown: Record<string, { count: number; won: number; win_rate: number | null }>
}

export const outcomesApi = {
  record: (estimateId: number, body: RecordOutcomeRequest) =>
    api.post<OutcomeResponse>(`/estimates/${estimateId}/outcome`, body),
  stats: () =>
    api.get<OutcomeStats>('/estimates/stats'),
}

// ─── Prices ─────────────────────────────────────────────────────────────────

export const pricesApi = {
  getCache: () => api.get('/prices/cache'),
  refresh: () => api.post('/prices/refresh'),
}

// ─── Pricing Templates ───────────────────────────────────────────────────────

export interface PricingTemplateSummary {
  id: string
  name: string
  description?: string | null
  sku?: string | null
  base_price?: number | null
  region?: string | null
  tags?: string[]
}

export const templatesApi = {
  list: () => api.get<PricingTemplateSummary[]>('/templates/pricing'),
  get: (id: string) => api.get<PricingTemplateSummary & Record<string, unknown>>(`/templates/pricing/${encodeURIComponent(id)}`),
}
