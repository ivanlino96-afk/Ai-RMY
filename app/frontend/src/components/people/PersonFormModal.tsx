import { useState } from 'react'
import { useCreatePerson } from '../../api/people'
import { ApiError } from '../../api/client'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { PhotoUploader } from './PhotoUploader'

interface PersonFormModalProps {
  onClose: () => void
}

export function PersonFormModal({ onClose }: PersonFormModalProps) {
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const createPerson = useCreatePerson()

  const submit = () => {
    if (!photo) {
      setError('A photo is required to enroll a face.')
      return
    }
    setError(null)
    createPerson.mutate(
      { name, notes, photo },
      {
        onSuccess: onClose,
        onError: (mutationError) => {
          setError(
            mutationError instanceof ApiError && mutationError.status === 422
              ? 'No face detected in that photo — try a clearer, front-facing shot.'
              : 'Enrollment failed. Try again.',
          )
        },
      },
    )
  }

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-void/80 p-6">
      <CornerBracketPanel title="Enroll face" className="w-full max-w-sm bg-void">
        <div className="space-y-3">
          <PhotoUploader onSelect={setPhoto} />

          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Name"
            className="w-full border border-hairline bg-void px-2 py-2 text-sm text-ink placeholder:text-ink-dim focus:border-lock focus:outline-none"
          />
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className="w-full resize-none border border-hairline bg-void px-2 py-2 text-sm text-ink placeholder:text-ink-dim focus:border-lock focus:outline-none"
          />

          {error ? <p className="text-xs text-alert">{error}</p> : null}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={submit}
              disabled={!name || createPerson.isPending}
              className="flex-1 border border-hairline px-3 py-2 text-xs uppercase tracking-[0.1em] text-lock hover:border-lock disabled:opacity-40"
            >
              {createPerson.isPending ? 'Enrolling…' : 'Enroll'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-hairline px-3 py-2 text-xs uppercase tracking-[0.1em] text-ink-dim hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </div>
      </CornerBracketPanel>
    </div>
  )
}
