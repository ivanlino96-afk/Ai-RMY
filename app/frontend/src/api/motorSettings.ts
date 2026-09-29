import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

export type SpeedProfile = 'manual' | 'automatic'
export interface MotorSpeeds { pan: number; tilt: number; pan_acceleration: number; tilt_acceleration: number }
export type MotorSpeedSettings = Record<SpeedProfile, MotorSpeeds>
const key = ['motor-speeds']

export function useMotorSpeeds() {
  return useQuery({ queryKey: key, queryFn: () => api.get<MotorSpeedSettings>('/api/settings/motor-speeds') })
}
export function useSaveMotorSpeeds(profile: SpeedProfile) {
  const query = useQueryClient()
  return useMutation({
    mutationFn: (speeds: MotorSpeeds) => api.post<MotorSpeedSettings>(`/api/settings/motor-speeds/${profile}`, speeds),
    onSuccess: data => query.setQueryData(key, data),
  })
}
