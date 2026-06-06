import type { Metadata } from 'next'
import { PipelinePage } from '@/components/pipeline/PipelinePage'

export const metadata: Metadata = {
  title: 'Pipeline – PlumbPrice AI',
  description: 'Track open bids and won work across your plumbing jobs.',
}

export default function Pipeline() {
  return <PipelinePage />
}
