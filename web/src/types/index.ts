export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  estimate?: EstimateBreakdown
  confidence?: number
  confidence_label?: string
  assumptions?: string[]
  timestamp: Date
}

export interface EstimateBreakdown {
  labor_total: number
  materials_total: number
  tax_total: number
  markup_total: number
  misc_total: number
  subtotal: number
  grand_total: number
  line_items: LineItem[]
}

export interface LineItem {
  line_type: string
  description: string
  quantity: number
  unit: string
  unit_cost: number
  total_cost: number
  supplier?: string
  sku?: string
}

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

export interface ProjectPipelineItem {
  id: number
  name: string
  job_type: string
  status: string
  customer_name?: string
  county: string
  city: string
  estimate_count: number
  latest_estimate_total?: number | null
  created_at: string
}

export type JobType = 'service' | 'construction' | 'commercial'
export type County = 'Dallas' | 'Tarrant' | 'Collin' | 'Denton' | 'Rockwall' | 'Parker'
