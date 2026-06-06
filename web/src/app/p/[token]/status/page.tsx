import type { Metadata } from 'next'
import { CustomerStatusPage } from '@/components/public-proposal/CustomerStatusPage'

interface Props {
  params: Promise<{ token: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { token } = await params
  try {
    const apiBase = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
    const res = await fetch(`${apiBase}/api/v1/public/proposals/${token}/status`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) {
      return { title: 'Project Status – PlumbPrice AI' }
    }
    const data = await res.json()
    return {
      title: `${data.project_name ?? 'Project Status'} – PlumbPrice AI`,
      description: 'Track your plumbing project schedule and milestones.',
    }
  } catch {
    return { title: 'Project Status – PlumbPrice AI' }
  }
}

export default function Page() {
  return <CustomerStatusPage />
}
