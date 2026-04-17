import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { listDocuments, uploadDocument, deleteDocument, type DocumentItem } from '@/lib/api'

// ─── Query keys ─────────────────────────────────────────────────────────────

export const documentKeys = {
  all: ['documents'] as const,
}

// ─── Queries ────────────────────────────────────────────────────────────────

export function useDocuments(
  options?: Partial<UseQueryOptions<DocumentItem[]>>,
) {
  return useQuery({
    queryKey: documentKeys.all,
    queryFn: listDocuments,
    ...options,
  })
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useUploadDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, docType, supplierId }: { file: File; docType: string; supplierId?: string }) =>
      uploadDocument(file, docType, supplierId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}
