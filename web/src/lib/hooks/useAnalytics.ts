import { useQuery } from '@tanstack/react-query'
import {
  analyticsApi,
  type OutcomeStats,
  type OutcomeListItem,
  type RevenueData,
  type PipelineAnalytics,
  type RepPerformance,
} from '@/lib/api'

export type { RevenueData, PipelineAnalytics, RepPerformance }

export const analyticsKeys = {
  all: ['analytics'] as const,
  stats: () => [...analyticsKeys.all, 'estimate-stats'] as const,
  outcomes: () => [...analyticsKeys.all, 'outcomes'] as const,
}

export function useEstimateStats() {
  return useQuery<OutcomeStats>({
    queryKey: analyticsKeys.stats(),
    queryFn: analyticsApi.getEstimateStats,
  })
}

export function useOutcomes() {
  return useQuery<OutcomeListItem[]>({
    queryKey: analyticsKeys.outcomes(),
    queryFn: analyticsApi.getOutcomes,
  })
}

export function useRevenue(period: string = 'all') {
  return useQuery<RevenueData>({
    queryKey: [...analyticsKeys.all, 'revenue', period],
    queryFn: () => analyticsApi.getRevenue(period),
  })
}

export function usePipelineAnalytics() {
  return useQuery<PipelineAnalytics>({
    queryKey: [...analyticsKeys.all, 'pipeline-analytics'],
    queryFn: analyticsApi.getPipelineAnalytics,
  })
}

export function useRepPerformance(period: string = 'all') {
  return useQuery<{ period: string; reps: RepPerformance[] }>({
    queryKey: [...analyticsKeys.all, 'rep-performance', period],
    queryFn: () => analyticsApi.getRepPerformance(period),
  })
}
