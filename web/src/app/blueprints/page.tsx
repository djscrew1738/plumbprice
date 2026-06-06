import type { Metadata } from 'next'
import { BlueprintsPage } from '@/components/blueprints/BlueprintsPage'

export const metadata: Metadata = {
  title: 'Blueprints – PlumbPrice AI',
  description: 'Upload blueprints for AI-powered takeoff and estimating.',
}

export default function BlueprintsRoute() {
  return <BlueprintsPage />
}
