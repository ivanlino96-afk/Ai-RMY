import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { GimbalStatus } from '../types/api'

const STATUS_KEY = ['gimbal-status']

export function useGimbalStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: () => api.get<GimbalStatus>('/api/gimbal/status'),
    refetchInterval: 500,
  })
}

export function useCenterGimbal() {
  return useMutation({
    mutationFn: () => api.post('/api/gimbal/center'),
  })
}

export function useHomeGimbal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/api/gimbal/home'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}

export function useSetTrackingMode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (enabled: boolean) => {
      const result = await api.post<{ ok: boolean; tracking_enabled: boolean }>('/api/tracking/mode', { enabled })
      if (!result.ok) throw new Error('No se pudo cambiar el seguimiento. Desactiva la alarma o termina el escaneo e inténtalo de nuevo.')
      return result
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}

interface JogDelta {
  pan_deg?: number
  tilt_deg?: number
}

export function useJogGimbal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (delta: JogDelta) => api.post<{ ok: boolean }>('/api/gimbal/jog', delta),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}

export function useStopGimbal() {
  return useMutation({
    mutationFn: () => api.post('/api/gimbal/stop'),
  })
}
