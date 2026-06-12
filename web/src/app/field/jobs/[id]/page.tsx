import type { Metadata } from 'next'
import { redirect } from 'next/navigation'

interface PageProps {
  params: Promise<{ id: string }>
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  return {
    title: `Job #${id} – PlumbPrice AI`,
  }
}

export default async function FieldJobDetailPage({ params }: PageProps) {
  const { id } = await params
  redirect(`/estimates/${id}`)
}
