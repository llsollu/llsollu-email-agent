import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ProjectInfo } from '@/lib/types'

export function useProjects(agentId: string, includeArchived = false) {
  return useQuery({
    queryKey: ['projects', agentId, includeArchived],
    queryFn: () => api.projects(agentId, includeArchived),
    // N+1 제거 + 반환 상한 적용으로 이제 목록이 가벼워 폴링 안전 → 새 메일 자동 반영.
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}

/** 상태 변경 — 낙관적 업데이트 + 실패 시 롤백. */
export function useMoveProject(agentId: string, includeArchived = false) {
  const qc = useQueryClient()
  const key = ['projects', agentId, includeArchived]
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
