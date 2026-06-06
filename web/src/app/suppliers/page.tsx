import type { Metadata } from 'next'
import { SuppliersPage } from '@/components/suppliers/SuppliersPage'

export const metadata: Metadata = {
  title: 'Suppliers – PlumbPrice AI',
  description: 'Compare catalog pricing across plumbing suppliers.',
}

export default function Suppliers() {
  return <SuppliersPage />
}
