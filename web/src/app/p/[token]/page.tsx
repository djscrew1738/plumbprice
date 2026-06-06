import type { Metadata } from 'next'
import { PublicProposalPage } from '@/components/public-proposal/PublicProposalPage'

interface Props {
  params: Promise<{ token: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { token } = await params
  try {
    const apiBase = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
    const res = await fetch(`${apiBase}/api/v1/public/proposals/${token}`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) {
      return { title: 'Proposal – PlumbPrice AI' }
    }
    const data = await res.json()
    return {
      title: `${data.estimate?.title ?? 'Proposal'} – PlumbPrice AI`,
      description: `View your plumbing estimate proposal from ${data.company?.name ?? 'PlumbPrice AI'}.`,
    }
  } catch {
    return { title: 'Proposal – PlumbPrice AI' }
  }
}

export default function Page() {
  return <PublicProposalPage />
}
