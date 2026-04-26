import axios from 'axios'
import type { ProjectPipelineResponse, ProjectPipelineItem } from '@/types'
export type OutcomeValue = 'won' | 'lost' | 'pending' | 'no_bid'

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
  withCredentials: true,
  timeout: 30_000,
})

// On 401, clear session and redirect to login
api.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401 && typeof window !== 'undefined') {
      // Best effort server-side cookie clear for HttpOnly auth cookie.
      void fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
      if (!window.location.pathname.startsWith('/login')) window.location.href = '/login'
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
  project_id?: number | null
  customer?: {
    name?: string
    email?: string
    phone?: string
    address?: string
  } | null
}

export interface ChatPriceStreamEvent {
  type: 'pricing' | 'token' | 'done' | 'error'
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
  // error event payload
  error?: string
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
    const base = typeof window === 'undefined'
      ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
      : ''
    const res = await fetch(`${base}/api/v1/chat/price/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
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
            } else if (currentEvent === 'error') {
              yield { type: 'error', error: (payload as {error?: string}).error ?? 'Generation failed' }
            }
          } catch (parseErr) {
            // Malformed SSE payload — log + surface to caller instead of silently dropping.
            // Pricing stream is critical; consumers should be able to show an error toast.
            // eslint-disable-next-line no-console
            console.warn('[SSE] failed to parse event', { event: currentEvent, raw, error: parseErr })
            if (currentEvent === 'pricing' || currentEvent === 'error') {
              yield { type: 'error', error: 'Malformed server event' }
            }
            // For 'token'/'done' or unknown events, continue — they're not fatal.
          }
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
  valid_until?: string | null
  is_expired?: boolean
  outcome?: OutcomeValue | null
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
  updateLineItems: (id: number, lineItems: LineItemPayload[]) =>
    api.put(`/estimates/${id}/line-items`, { line_items: lineItems }),
  update: (id: number, body: { line_items: Array<Omit<LineItemPayload, 'trace_json' | 'canonical_item'> & { canonical_item?: string | null }> }) =>
    api.patch(`/estimates/${id}`, body),
  delete: (id: number) =>
    api.delete(`/estimates/${id}`),
  duplicate: (id: number) =>
    api.post(`/estimates/${id}/duplicate`, {}),
  getCostBreakdown: (id: number) =>
    api.get(`/estimates/${id}/cost-breakdown`),
  getVersions: (id: number) =>
    api.get(`/estimates/${id}/versions`),
  getVersion: (id: number, versionId: string) =>
    api.get(`/estimates/${id}/versions/${versionId}`),
  diffVersions: (id: number, v1: string, v2: string) =>
    api.get(`/estimates/${id}/versions/diff`, { params: { v1, v2 } }),
  suggestAddons: (taskCodes: string[], maxSuggestions = 8) =>
    api.post<Array<{ task_code: string; rationale: string; severity: 'code_required' | 'recommended' | 'best_practice' }>>(
      '/estimates/suggest-addons',
      { task_codes: taskCodes, max_suggestions: maxSuggestions },
    ),
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
  listFlags: () => api.get<FlagRow[]>('/admin/flags'),
  toggleFlag: (key: string, enabled: boolean) =>
    api.put<{ key: string; enabled: boolean }>(`/admin/flags/${encodeURIComponent(key)}`, { enabled }),
  upsertFlag: (body: { key: string; enabled: boolean; description?: string | null }) =>
    api.post<{ key: string; enabled: boolean; description?: string | null }>('/admin/flags', body),
  deleteFlag: (key: string) => api.delete(`/admin/flags/${encodeURIComponent(key)}`),
}

export interface FlagRow {
  key: string
  enabled: boolean
  description?: string | null
  updated_at?: string | null
}

export const flagsApi = {
  list: () => api.get<Record<string, boolean>>('/flags'),
}

// ─── Blueprints ─────────────────────────────────────────────────────────────

export const blueprintsApi = {
  upload: (file: File, metadata?: Record<string, string>) => {
    const form = new FormData()
    form.append('file', file)
    if (metadata) {
      Object.entries(metadata).forEach(([k, v]) => form.append(k, v))
    }
    return api.post('/blueprints/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
    })
  },
  list: () =>
    api.get('/blueprints/'),
  getStatus: (jobId: string) =>
    api.get(`/blueprints/${jobId}/status`),
  getTakeoff: (jobId: string) =>
    api.get(`/blueprints/${jobId}/takeoff`),
  toEstimate: (jobId: string | number, body?: { project_id?: number }) =>
    api.post(`/blueprints/${jobId}/to-estimate`, body ?? {}),
  delete: (jobId: string) =>
    api.delete(`/blueprints/${jobId}`),
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
  public_token?: string | null
  accept_url?: string | null
}

export interface ProposalListItem {
  id: number
  estimate_id: number
  customer_name: string | null
  recipient_email: string | null
  status: 'draft' | 'sent' | 'viewed' | 'accepted' | 'declined'
  grand_total: number
  scope_summary: string | null
  pdf_url: string | null
  created_at: string
  sent_at: string | null
}

export interface ProposalDetail extends ProposalListItem {
  estimate_ref: string | null
  message: string | null
}

export const proposalsApi = {
  send: (estimateId: number, body: SendProposalRequest) =>
    api.post<SendProposalResponse>(`/proposals/${estimateId}/send`, body),
  listSends: (estimateId: number) =>
    api.get<Array<{
      id: number
      recipient_email: string
      recipient_name: string | null
      sent_at: string | null
      created_at: string
      public_token?: string | null
      token_expires_at?: string | null
      opened_at?: string | null
      accepted_at?: string | null
      declined_at?: string | null
      client_signature?: string | null
      status?: string
    }>>(`/proposals/${estimateId}/sends`),
  generate: (body: { estimate_id: number }) =>
    api.post<ProposalDetail>('/proposals/generate', body),
  list: (params?: { status?: string; search?: string }) =>
    api.get<ProposalListItem[]>('/proposals/', { params }),
  get: (id: number) =>
    api.get<ProposalDetail>(`/proposals/${id}`),
  resend: (id: number) =>
    api.post<SendProposalResponse>(`/proposals/${id}/send`, {}),
  downloadPdf: (id: number) =>
    api.get(`/proposals/${id}/pdf`, { responseType: 'blob' }),
}

// ─── Sessions ────────────────────────────────────────────────────────────────

export interface ChatSessionSummary {
  id: number
  title: string | null
  county: string | null
  message_count?: number
  last_message_at?: string | null
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
  getMessages: (id: number) =>
    api.get<ChatSessionDetail['messages']>(`/sessions/${id}/messages`),
  clone: (id: number) =>
    api.post<ChatSessionSummary>(`/sessions/${id}/clone`, {}),
}

// ─── Outcomes ────────────────────────────────────────────────────────────────

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

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface OutcomeListItem {
  id: number
  estimate_id: number
  outcome: OutcomeValue
  final_price: number | null
  notes: string | null
  created_at: string
  updated_at: string
  estimate_title: string | null
  estimate_grand_total: number | null
  job_type: string | null
  confidence_score: number | null
  county: string | null
}

// ─── Analytics extended types ────────────────────────────────────────────────

export interface RevenueData {
  period: string
  total_revenue: number
  monthly_breakdown: { month: string; revenue: number; estimate_count: number }[]
  by_job_type: { job_type: string; revenue: number; count: number }[]
}

export interface PipelineAnalytics {
  stages: { name: string; count: number; avg_days: number }[]
  active_pipeline_value: number
  conversion_rate: number
}

export interface RepPerformance {
  user_id: number
  full_name: string
  quotes_created: number
  won_count: number
  won_amount: number
  avg_deal_size: number
}

export const analyticsApi = {
  getEstimateStats: async () => (await api.get<OutcomeStats>('/estimates/stats')).data,
  getOutcomes: async () => (await api.get<OutcomeListItem[]>('/outcomes/')).data,
  getRevenue: async (period = 'all') => (await api.get<RevenueData>(`/analytics/revenue?period=${period}`)).data,
  getPipelineAnalytics: async () => (await api.get<PipelineAnalytics>('/analytics/pipeline')).data,
  getRepPerformance: async (period = 'all') => (await api.get<{ period: string; reps: RepPerformance[] }>(`/analytics/rep-performance?period=${period}`)).data,
}

// ─── Notifications ──────────────────────────────────────────────────────

export interface BackendNotification {
  id: number
  kind: string
  title: string
  body: string | null
  link: string | null
  read_at: string | null
  created_at: string
}

export const notificationsApi = {
  list: async (params: { limit?: number; unread_only?: boolean } = {}) => {
    const qs = new URLSearchParams()
    qs.set('limit', String(params.limit ?? 20))
    if (params.unread_only) qs.set('unread_only', 'true')
    const res = await api.get<BackendNotification[]>(`/notifications?${qs.toString()}`)
    return res.data
  },
  unreadCount: async () => (await api.get<{ count: number }>('/notifications/unread-count')).data.count,
  markRead: async (ids: number[]) =>
    (await api.post('/notifications/mark-read', { ids })).data,
  markAllRead: async () =>
    (await api.post('/notifications/mark-read', { all: true })).data,
  delete: async (id: number) => (await api.delete(`/notifications/${id}`)).data,
}

// ─── Prices ─────────────────────────────────────────────────────────────────

export interface PriceCacheStats {
  cached_items: number
  hit_rate: number
  stale_count: number
  last_refresh: string | null
}

export interface PriceHistoryEntry {
  price: number
  date: string
  supplier?: string
  change_pct?: number
}

export interface PriceHistoryResponse {
  item_id: string
  entries: PriceHistoryEntry[]
  min_price: number
  max_price: number
  avg_price: number
  trend: 'up' | 'down' | 'stable'
}

export const pricesApi = {
  getCacheStats: async () => (await api.get<PriceCacheStats>('/prices/cache')).data,
  refresh: async (supplierId?: string) =>
    (await api.post('/prices/refresh', supplierId ? { supplier_id: supplierId } : {})).data,
  getHistory: async (itemId: string) =>
    (await api.get<PriceHistoryResponse>(`/prices/history/${encodeURIComponent(itemId)}`)).data,
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

// ─── Agent Memories ─────────────────────────────────────────────────────────

export type MemoryKind = 'preference' | 'profile' | 'customer' | 'job_history' | 'fact'

export interface AgentMemory {
  id: number
  kind: MemoryKind
  content: string
  importance: number
  metadata?: Record<string, unknown> | null
  source_session_id?: number | null
  created_at?: string | null
  last_referenced_at?: string | null
}

export const memoriesApi = {
  list: async (kind?: MemoryKind): Promise<AgentMemory[]> =>
    (await api.get('/memories', { params: kind ? { kind } : undefined })).data,
  create: async (body: { content: string; kind?: MemoryKind; importance?: number }): Promise<AgentMemory> =>
    (await api.post('/memories', body)).data,
  update: async (id: number, body: Partial<{ content: string; kind: MemoryKind; importance: number }>): Promise<AgentMemory> =>
    (await api.patch(`/memories/${id}`, body)).data,
  delete: async (id: number): Promise<void> => {
    await api.delete(`/memories/${id}`)
  },
  extractFromSession: async (session_id: number) =>
    (await api.post('/memories/extract', { session_id })).data,
}

// ─── User / Profile ─────────────────────────────────────────────────────────

export const userApi = {
  getProfile: async () => (await api.get('/auth/me')).data,
  updateProfile: async (data: { name?: string; email?: string; phone?: string }) =>
    (await api.patch('/auth/profile', data)).data,
  changePassword: async (data: { current_password: string; new_password: string }) =>
    (await api.post('/auth/change-password', data)).data,
  uploadAvatar: async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return (
      await api.post('/auth/avatar', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    ).data
  },
}

// ─── Organization ───────────────────────────────────────────────────────────

export const orgApi = {
  get: async () => (await api.get('/admin/organizations/me')).data,
  update: async (data: {
    name?: string
    address?: string
    phone?: string
    logo_url?: string
    billing_email?: string
    default_tax_rate?: number
    default_markup_percent?: number
  }) => (await api.patch('/admin/organizations/me', data)).data,
  uploadLogo: async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return (await api.post('/admin/organizations/me/logo', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })).data as { logo_url: string }
  },
  listUsers: async () => (await api.get('/admin/users')).data,
  inviteUser: async (data: { email: string; role: string; full_name?: string }) =>
    (await api.post('/admin/users/invite', data)).data,
  updateUserRole: async (userId: string, role: string) =>
    (await api.patch(`/admin/users/${userId}`, { role })).data,
  updateUser: async (
    userId: string,
    data: { role?: string; is_active?: boolean; full_name?: string },
  ) => (await api.patch(`/admin/users/${userId}`, data)).data,
  removeUser: async (userId: string) =>
    (await api.delete(`/admin/users/${userId}`)).data,
  listInvites: async () => (await api.get('/admin/invites')).data,
  revokeInvite: async (inviteId: string) =>
    (await api.delete(`/admin/invites/${inviteId}`)).data,
}

// ─── Documents ──────────────────────────────────────────────────────────────

export interface DocumentItem {
  id: string
  name: string
  doc_type: string
  status: string
  supplier_id?: string | null
  supplier_name?: string | null
  created_at: string
}

export async function uploadDocument(file: File, docType: string, supplierId?: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('doc_type', docType)
  if (supplierId) formData.append('supplier_id', supplierId)
  const res = await api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  })
  return res.data
}

export async function listDocuments() {
  return (await api.get<DocumentItem[]>('/documents/')).data
}

export async function getDocument(id: string) {
  return (await api.get<DocumentItem>(`/documents/${id}`)).data
}

export async function deleteDocument(id: string) {
  return (await api.delete(`/documents/${id}`)).data
}

export async function downloadDocument(id: number | string, filename: string) {
  const res = await api.get(`/documents/${id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
