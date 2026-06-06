import type { Metadata } from 'next'
import { cookies } from 'next/headers'
import { EstimateDetailPage } from '@/components/estimates/EstimateDetailPage'

const API_BASE =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000'

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>
}): Promise<Metadata> {
  const { id } = await params
  const numericId = Number(id)

  if (isNaN(numericId)) {
    return { title: 'Estimate – PlumbPrice AI' }
  }

  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('pp_token')?.value
    const res = await fetch(`${API_BASE}/api/v1/estimates/${numericId}`, {
      headers: token ? { Cookie: `pp_token=${token}` } : {},
      next: { revalidate: 0 },
    })

    if (!res.ok) throw new Error()

    const data = (await res.json()) as { title?: string }
    return {
      title: data.title
        ? `${data.title} – PlumbPrice AI`
        : `Estimate #${numericId} – PlumbPrice AI`,
    }
  } catch {
    return { title: `Estimate #${numericId} – PlumbPrice AI` }
  }
}

export default function Page() {
  return <EstimateDetailPage />
}
