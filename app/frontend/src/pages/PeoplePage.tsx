import { useState } from 'react'
import { usePeople } from '../api/people'
import { PeopleList } from '../components/people/PeopleList'
import { EnrollmentFlow } from '../components/people/EnrollmentFlow'
import { PageHeader } from '../components/hud/PageHeader'

export function PeoplePage() {
  const { data: people, isLoading } = usePeople()
  const [enrolling, setEnrolling] = useState(false)

  return (
    <div>
      <PageHeader
        code="SYS-02"
        title="Known faces"
        action={
          <button
            type="button"
            onClick={() => setEnrolling(true)}
            className="border border-hairline px-3 py-2 text-xs text-ink hover:border-accent hover:text-accent"
          >
            Enroll face
          </button>
        }
      />

      {isLoading ? (
        <p className="text-sm text-ink-dim">Loading…</p>
      ) : (
        <PeopleList people={people ?? []} />
      )}

      {enrolling ? (
        <EnrollmentFlow onClose={() => setEnrolling(false)} onComplete={() => setEnrolling(false)} />
      ) : null}
    </div>
  )
}
