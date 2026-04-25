import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { listDocuments, uploadDocument, deleteDocument, type DocumentItem } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

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
    staleTime: 5 * 60_000,
    queryFn: listDocuments,
    ...options,
  })
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useUploadDocument() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: ({ file, docType, supplierId }: { file: File; docType: string; supplierId?: string }) =>
      uploadDocument(file, docType, supplierId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
    onError: () => {
      toast.error('Failed to upload document')
    },
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: documentKeys.all })
      const previous = queryClient.getQueryData<DocumentItem[]>(documentKeys.all)
      queryClient.setQueryData<DocumentItem[]>(
        documentKeys.all,
        (old) => old?.filter(d => d.id !== id),
      )
      return { previous }
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(documentKeys.all, context.previous)
      }
      toast.error('Failed to delete document')
    },
    onSuccess: () => {
      toast.success('Document deleted')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}
