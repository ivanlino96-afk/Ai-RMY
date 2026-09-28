import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { ScanConfigInput, ScanStatus } from '../types/api'

const STATUS_KEY = ['scan-status']

// Fallback for the initial render / a page reload -- once live, scan
// progress rides the existing detection WebSocket event (detection.scan),
// same as tracking_offset, so this isn't polled continuously.
export function useScanStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: () => api.get<ScanStatus>('/api/scan/status'),
  })
}

export function useStartScan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (config: ScanConfigInput) =>
      api.post<{ ok: boolean }>('/api/scan/start', config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}

export function useCancelScan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ ok: boolean }>('/api/scan/cancel'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}
