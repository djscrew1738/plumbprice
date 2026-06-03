import type { Metadata } from 'next'
import { cookies } from 'next/headers'
import type { ReactNode } from 'react'

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
    return { title: 'Project – PlumbPrice AI' }
  }

  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('pp_token')?.value
    const res = await fetch(`${API_BASE}/api/v1/projects/${numericId}`, {
      headers: token ? { Cookie: `pp_token=${token}` } : {},
      next: { revalidate: 0 },
    })

    if (!res.ok) throw new Error()

    const data = (await res.json()) as { name?: string }
    return {
      title: data.name
        ? `${data.name} – PlumbPrice AI`
        : `Project #${numericId} – PlumbPrice AI`,
    }
  } catch {
    return { title: `Project #${numericId} – PlumbPrice AI` }
  }
}

export default function ProjectLayout({ children }: { children: ReactNode }) {
  return <>{children}</>
}
