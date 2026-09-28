import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { CameraList } from '../types/api'

const LIST_KEY = ['camera-list']

// No refetchInterval: enumerating devices briefly opens/closes each one, so
// this only runs on mount and when the user explicitly refreshes.
export function useCameraList() {
  return useQuery({
    queryKey: LIST_KEY,
    queryFn: () => api.get<CameraList>('/api/camera/list'),
  })
}

export function useSelectCamera() {
  // No query invalidation here: selecting a camera doesn't change which
  // devices exist, and refetching the list right after select would probe
  // (open/close) every device index -- including the one just selected --
  // while the pipeline thread is mid-open on it. On Windows that race can
  // make the real open fail (VIDEOIO backend throws on concurrent access).
  return useMutation({
    mutationFn: (deviceIndex: number | null) =>
      api.post<{ ok: boolean; device_index: number | null }>('/api/camera/select', {
        device_index: deviceIndex,
      }),
  })
}
