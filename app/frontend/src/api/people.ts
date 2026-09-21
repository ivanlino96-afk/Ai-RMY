import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { EnrollmentPhotoResult, EnrollmentSessionStart, Person, PersonInput } from '../types/api'

const PEOPLE_KEY = ['people']

export function usePeople() {
  return useQuery({
    queryKey: PEOPLE_KEY,
    queryFn: () => api.get<Person[]>('/api/people'),
  })
}

// -- guided 3-photo enrollment session (RF-1, RF-2, RF-4, RF-5, RF-6) -------
// `personId` starts a photo-recapture session for an existing person
// (RF-8) instead of a brand new alta; omit it for a new person.

export function useStartEnrollment() {
  return useMutation({
    mutationFn: (personId?: number) =>
      api.post<EnrollmentSessionStart>(
        `/api/people/enroll${personId != null ? `?person_id=${personId}` : ''}`,
      ),
  })
}

export function useSubmitEnrollmentPhoto() {
  return useMutation({
    mutationFn: ({ sessionId, photo }: { sessionId: string; photo: Blob }) => {
      const form = new FormData()
      form.set('photo', photo, 'capture.jpg')
      return api.postForm<EnrollmentPhotoResult>(`/api/people/enroll/${sessionId}/photo`, form)
    },
  })
}

export function useCancelEnrollment() {
  return useMutation({
    mutationFn: (sessionId: string) => api.delete(`/api/people/enroll/${sessionId}`),
  })
}

export function useFinalizeEnrollment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, input }: { sessionId: string; input: PersonInput }) =>
      api.post<Person>(`/api/people/enroll/${sessionId}/finalize`, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PEOPLE_KEY }),
  })
}

// -- editing / deleting an existing person (RF-8, RF-9) ----------------------

export function useUpdatePerson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { id: number } & Partial<PersonInput>) => {
      const { id, ...patch } = input
      return api.patch<Person>(`/api/people/${id}`, patch)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PEOPLE_KEY }),
  })
}

export function useDeletePerson() {
  const queryClient = useQueryClient()
  return useMutation({
    // The confirmation step happens in the UI before this is ever called
    // (RF-9) — by the time it fires, confirm=true is always correct.
    mutationFn: (id: number) => api.delete(`/api/people/${id}?confirm=true`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PEOPLE_KEY }),
  })
}
