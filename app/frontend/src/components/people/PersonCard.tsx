import { useState } from 'react'
import type { SyntheticEvent } from 'react'
import { useDeletePerson, useUpdatePerson } from '../../api/people'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import type { Person } from '../../types/api'

interface PersonCardProps {
  person: Person
}

export function PersonCard({ person }: PersonCardProps) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(person.name)
  const [notes, setNotes] = useState(person.notes)
  const updatePerson = useUpdatePerson()
  const deletePerson = useDeletePerson()

  const save = () => {
    updatePerson.mutate({ id: person.id, name, notes }, { onSuccess: () => setEditing(false) })
  }

  const hidePhoto = (event: SyntheticEvent<HTMLImageElement>) => {
    event.currentTarget.style.display = 'none'
  }

  return (
    <CornerBracketPanel>
      <div className="mb-3 aspect-square w-full border border-hairline bg-void">
        <img
          src={`/api/people/${person.id}/photo`}
          alt={person.name}
          onError={hidePhoto}
          className="h-full w-full object-cover"
        />
      </div>

      {editing ? (
        <div className="space-y-2">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="w-full border border-hairline bg-void px-2 py-1 text-sm text-ink focus:border-lock focus:outline-none"
          />
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={2}
            className="w-full resize-none border border-hairline bg-void px-2 py-1 text-sm text-ink focus:border-lock focus:outline-none"
          />
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
              onClick={() => setEditing(false)}
              className="flex-1 border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink-dim hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="truncate text-sm text-ink">{person.name}</p>
          {person.notes ? <p className="truncate text-xs text-ink-dim">{person.notes}</p> : null}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="flex-1 border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink hover:border-lock hover:text-lock"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => deletePerson.mutate(person.id)}
              disabled={deletePerson.isPending}
              className="flex-1 border border-hairline px-2 py-1 text-xs uppercase tracking-[0.1em] text-ink hover:border-alert hover:text-alert disabled:opacity-40"
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </CornerBracketPanel>
  )
}
