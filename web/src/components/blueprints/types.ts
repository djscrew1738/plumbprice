export interface TakeoffFixture {
  name: string
  quantity: number
  confidence: number
  unit?: string
}

export interface TakeoffResult {
  fixtures: TakeoffFixture[]
  rooms: Array<{
    type: string
    name: string | null
    area_sqft: number | null
    fixture_count: number | null
    confidence: number
  }>
  pipe_runs: Array<{
    pipe_type: string
    length_ft: number
    confidence: number
  }>
}
