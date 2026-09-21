import { useState } from 'react'
import type { SyntheticEvent } from 'react'
import { useDeletePerson, useUpdatePerson } from '../../api/people'
import { ApiError } from '../../api/client'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { EnrollmentFlow } from './EnrollmentFlow'
import type { Person } from '../../types/api'

interface PersonCardProps {
  person: Person
}

const inputClass =
  'w-full border border-hairline bg-void px-2 py-1 text-sm text-ink focus:border-lock focus:outline-none'

export function PersonCard({ person }: PersonCardProps) {
  const [editing, setEditing] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [recapturing, setRecapturing] = useState(false)
  const [photoVersion, setPhotoVersion] = useState(0)

  const [name, setName] = useState(person.name)
  const [age, setAge] = useState(String(person.age))
  const [email, setEmail] = useState(person.email)
  const [phone, setPhone] = useState(person.phone)
  const [notes, setNotes] = useState(person.notes)
  const [error, setError] = useState<string | null>(null)

  const updatePerson = useUpdatePerson()
  const deletePerson = useDeletePerson()

  const save = () => {
    setError(null)
    updatePerson.mutate(
      { id: person.id, name, age: Number(age), email, phone, notes },
      {
        onSuccess: () => setEditing(false),
        onError: (mutationError) =>
          setError(mutationError instanceof ApiError ? mutationError.message : 'Update failed. Try again.'),
      },
    )
  }

  const hidePhoto = (event: SyntheticEvent<HTMLImageElement>) => {
    event.currentTarget.style.display = 'none'
  }

  return (
    <CornerBracketPanel>
      <div className="mb-3 aspect-square w-full border border-hairline bg-void">
        <img
          src={`/api/people/${person.id}/photo?v=${photoVersion}`}
          alt={person.name}
          onError={hidePhoto}
          className="h-full w-full object-cover"
        />
      </div>

      {editing ? (
        <div className="space-y-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className={inputClass} />
          <input
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder="Age"
            type="number"
            className={inputClass}
          />
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            type="email"
            className={inputClass}
          />
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone" className={inputClass} />
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className={`resize-none ${inputClass}`}
          />
          {error ? <p className="text-xs text-alert">{error}</p> : null}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={save}
              disabled={updatePerson.isPending}
              className="flex-1 border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-lock hover:border-lock disabled:opacity-40"
            >
              Save
            </button>
            <button
              type="button"
              onClick={() => {
                setEditing(false)
                setError(null)
              }}
              className="flex-1 border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink-dim hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : confirmingDelete ? (
        <div className="space-y-2">
          <p className="text-xs text-alert">Delete {person.name} and all their data? This can't be undone.</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => deletePerson.mutate(person.id)}
              disabled={deletePerson.isPending}
              className="flex-1 border border-alert px-2 py-1 text-xs uppercase tracking-[0.1em] text-alert hover:bg-alert hover:text-void disabled:opacity-40"
            >
              Confirm delete
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(false)}
              className="flex-1 border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink-dim hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="truncate text-sm text-ink">{person.name}</p>
          <p className="truncate text-xs text-ink-dim">{person.email}</p>
          {person.notes ? <p className="truncate text-xs text-ink-dim">{person.notes}</p> : null}
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink hover:border-lock hover:text-lock"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => setRecapturing(true)}
              className="border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink hover:border-lock hover:text-lock"
            >
              Retake photos
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="col-span-2 border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink hover:border-alert hover:text-alert"
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {recapturing ? (
        <EnrollmentFlow
          person={person}
          onClose={() => setRecapturing(false)}
          onComplete={() => {
            setRecapturing(false)
            setPhotoVersion((v) => v + 1)
          }}
        />
      ) : null}
    </CornerBracketPanel>
  )
}
