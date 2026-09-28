import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { DefenseStatus } from '../types/api'

const STATUS_KEY = ['defense-status']

// Fallback for the initial render / a page reload -- once live, defense
// status rides the existing detection WebSocket event (detection.defense),
// same as scan, so this is only a 3s-interval backstop.
export function useDefenseStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: () => api.get<DefenseStatus>('/api/defense/status'),
    refetchInterval: 3000,
  })
}

export function useArmDefense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ ok: boolean }>('/api/defense/arm'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}

export function useDisarmDefense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ ok: boolean }>('/api/defense/disarm'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}
