import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Person } from '../types/api'

const PEOPLE_KEY = ['people']

export function usePeople() {
  return useQuery({
    queryKey: PEOPLE_KEY,
    queryFn: () => api.get<Person[]>('/api/people'),
  })
}

export function useCreatePerson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { name: string; notes: string; photo: File }) => {
      const form = new FormData()
      form.set('name', input.name)
      form.set('notes', input.notes)
      form.set('photo', input.photo)
      return api.postForm<Person>('/api/people', form)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PEOPLE_KEY }),
  })
}

export function useUpdatePerson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { id: number; name?: string; notes?: string }) =>
      api.patch<Person>(`/api/people/${input.id}`, {
        name: input.name,
        notes: input.notes,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PEOPLE_KEY }),
  })
}

export function useDeletePerson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/api/people/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PEOPLE_KEY }),
  })
}
