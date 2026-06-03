import type { Metadata } from 'next'
import { DocumentsPage } from '@/components/documents/DocumentsPage'

export const metadata: Metadata = {
  title: 'Documents – PlumbPrice AI',
  description: 'Manage uploaded documents and supplier price sheets.',
}

export default function Documents() {
  return <DocumentsPage />
}
