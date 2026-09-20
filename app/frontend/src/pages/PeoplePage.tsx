import { useState } from 'react'
import { usePeople } from '../api/people'
import { PeopleList } from '../components/people/PeopleList'
import { PersonFormModal } from '../components/people/PersonFormModal'

export function PeoplePage() {
  const { data: people, isLoading } = usePeople()
  const [enrolling, setEnrolling] = useState(false)

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-sm tracking-[0.1em] text-ink-dim uppercase">Known faces</h1>
        <button
          type="button"
          onClick={() => setEnrolling(true)}
          className="border border-hairline px-3 py-2 text-xs uppercase tracking-[0.1em] text-ink hover:border-lock hover:text-lock"
        >
          Enroll face
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-ink-dim">Loading…</p>
      ) : (
        <PeopleList people={people ?? []} />
      )}

      {enrolling ? <PersonFormModal onClose={() => setEnrolling(false)} /> : null}
    </div>
  )
}
