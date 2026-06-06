import { api } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AdobeConnectionStatus {
  connected: boolean
  adobe_email?: string | null
  adobe_display_name?: string | null
  expires_at?: string | null
}

export interface AdobeFileItem {
  asset_id: string
  name: string
  modified?: string | null
  size_bytes?: number | null
  mime_type?: string | null
  thumbnail_url?: string | null
}

export interface AdobeFilesResponse {
  files: AdobeFileItem[]
  total: number
  offset: number
  limit: number
}

export interface AdobeImportResponse {
  job_id: number
  filename: string
  status: string
}

// ─── API client ───────────────────────────────────────────────────────────────

export const adobeApi = {
  /** Get the Adobe OAuth authorization URL to redirect the user to. */
  getAuthUrl: () =>
    api.get<{ auth_url: string }>('/adobe/auth/url'),

  /** Check if the current user has a connected Adobe account. */
  getStatus: () =>
    api.get<AdobeConnectionStatus>('/adobe/auth/status'),

  /** Remove stored Adobe tokens (disconnect). */
  disconnect: () =>
    api.delete('/adobe/auth/disconnect'),

  /** List PDF files from the user's Adobe Document Cloud. */
  listFiles: (params?: { limit?: number; offset?: number; search?: string }) =>
    api.get<AdobeFilesResponse>('/adobe/files', { params }),

  /** Download a DC file and queue it as a blueprint job. */
  importFile: (body: {
    asset_id: string
    filename?: string
    project_id?: number
  }) =>
    api.post<AdobeImportResponse>('/adobe/import', body),
}
