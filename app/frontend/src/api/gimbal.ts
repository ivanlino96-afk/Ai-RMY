import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { GimbalStatus } from '../types/api'

const STATUS_KEY = ['gimbal-status']

export function useGimbalStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: () => api.get<GimbalStatus>('/api/gimbal/status'),
    refetchInterval: 3000,
  })
}

export function useCenterGimbal() {
  return useMutation({
    mutationFn: () => api.post('/api/gimbal/center'),
  })
}

export function useSetTrackingMode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (enabled: boolean) => api.post('/api/tracking/mode', { enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}
