import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ProjectInfo } from '@/lib/types'

export function useProjects(agentId: string) {
  return useQuery({
    queryKey: ['projects', agentId],
    queryFn: () => api.projects(agentId),
    refetchInterval: 60_000,
  })
}

/** 상태 변경 — 낙관적 업데이트 + 실패 시 롤백. */
export function useMoveProject(agentId: string) {
  const qc = useQueryClient()
  const key = ['projects', agentId]
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.setProjectStatus(agentId, id, status),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: key })
      const prev = qc.getQueryData<ProjectInfo[]>(key)
      qc.setQueryData<ProjectInfo[]>(key, (old) =>
        old?.map((p) => (p.id === id ? { ...p, status } : p)),
      )
      return { prev }
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  })
}
