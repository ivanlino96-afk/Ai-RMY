import type { Person } from '../../types/api'
import { PersonCard } from './PersonCard'

interface PeopleListProps {
  people: Person[]
}

export function PeopleList({ people }: PeopleListProps) {
  if (people.length === 0) {
    return <p className="text-sm text-ink-dim">No known faces yet. Enroll one to get started.</p>
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {people.map((person) => (
        <PersonCard key={person.id} person={person} />
      ))}
    </div>
  )
}
