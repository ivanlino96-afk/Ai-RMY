import { useEffect, useRef, useState } from 'react'
import {
  useCancelEnrollment,
  useFinalizeEnrollment,
  useStartEnrollment,
  useSubmitEnrollmentPhoto,
} from '../../api/people'
import { ApiError } from '../../api/client'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { CaptureFrame } from './CaptureFrame'
import { POSE_ORDER, POSE_LABELS } from '../../constants'
import type { Person, PersonInput, Pose } from '../../types/api'

interface EnrollmentFlowProps {
  /** Set to re-capture an existing person's photos only (RF-8). Omit for a
   * brand new alta (RF-1..RF-7). */
  person?: Person
  onClose: () => void
  onComplete: (person: Person) => void
}

const inputClass =
  'w-full border border-hairline bg-void px-2 py-2 text-sm text-ink placeholder:text-ink-dim focus:border-lock focus:outline-none'

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Something went wrong. Try again.'
}

// Backs both T19 (new-person guided capture + data form) and T21's
// photo-only re-capture — the same 3-photo session flow from
// vision.enroll.EnrollmentSession serves both, differing only in whether
// `person` is set (see app/backend/routers/people.py's finalize branch).
export function EnrollmentFlow({ person, onClose, onComplete }: EnrollmentFlowProps) {
  const startEnrollment = useStartEnrollment()
  const submitPhoto = useSubmitEnrollmentPhoto()
  const cancelEnrollment = useCancelEnrollment()
  const finalizeEnrollment = useFinalizeEnrollment()

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [currentPose, setCurrentPose] = useState<Pose | null>(null)
  const [phase, setPhase] = useState<'capture' | 'form'>('capture')
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const startedRef = useRef(false)

  const [name, setName] = useState(person?.name ?? '')
  const [notes, setNotes] = useState(person?.notes ?? '')

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    startEnrollment.mutate(person?.id, {
      onSuccess: (result) => {
        setSessionId(result.session_id)
        setCurrentPose(result.next_pose)
      },
    })
    // Starts exactly once per mount — a fresh session per open modal.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const finalize = (sessionIdToUse: string, input: PersonInput) => {
    setFormError(null)
    finalizeEnrollment.mutate(
      { sessionId: sessionIdToUse, input },
      {
        onSuccess: (result) => onComplete(result),
        onError: (mutationError) => setFormError(errorMessage(mutationError)),
      },
    )
  }

  const cancel = () => {
    if (sessionId) cancelEnrollment.mutate(sessionId)
    onClose()
  }

  const handleCapture = (photo: Blob) => {
    if (!sessionId) return
    setPhotoError(null)
    submitPhoto.mutate(
      { sessionId, photo },
      {
        onSuccess: (result) => {
          if (!result.is_complete) {
            setCurrentPose(result.next_pose)
            return
          }
          if (person) {
            // RF-8: re-capturing photos never re-asks for the person's data.
            finalize(sessionId, {
              name: person.name,
              age: person.age,
              email: person.email,
              phone: person.phone,
              notes: person.notes,
            })
          } else {
            setPhase('form')
          }
        },
        onError: (mutationError) => setPhotoError(errorMessage(mutationError)),
      },
    )
  }

  const submitForm = () => {
    if (!sessionId) return
    finalize(sessionId, { name, notes })
  }

  const title = person ? 'Retake photos' : 'Enroll face'
  const poseNumber = currentPose ? POSE_ORDER.indexOf(currentPose) + 1 : POSE_ORDER.length

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-void/80 p-6">
      <CornerBracketPanel title={title} className="w-full max-w-sm bg-void">
        {phase === 'capture' ? (
          <div className="space-y-3">
            <p className="text-xs text-ink-dim">
              Photo {poseNumber} of {POSE_ORDER.length}
              {currentPose ? ` — ${POSE_LABELS[currentPose]}` : ''}
            </p>

            <CaptureFrame
              onCapture={handleCapture}
              disabled={!sessionId || submitPhoto.isPending || finalizeEnrollment.isPending}
            />

            {photoError ? <p className="text-xs text-alert">{photoError}</p> : null}
            {person && finalizeEnrollment.isPending ? (
              <p className="text-xs text-ink-dim">Saving new photos…</p>
            ) : null}
            {formError ? <p className="text-xs text-alert">{formError}</p> : null}

            <button
              type="button"
              onClick={cancel}
              className="w-full border border-hairline px-3 py-2 text-xs uppercase tracking-[0.1em] text-ink-dim hover:text-ink"
            >
              Cancel
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className={inputClass} />
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notes (optional)"
              rows={2}
              className={`resize-none ${inputClass}`}
            />

            {formError ? <p className="text-xs text-alert">{formError}</p> : null}

            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={submitForm}
                disabled={!name || finalizeEnrollment.isPending}
                className="flex-1 border border-hairline px-3 py-2 text-xs uppercase tracking-[0.1em] text-lock hover:border-lock disabled:opacity-40"
              >
                {finalizeEnrollment.isPending ? 'Saving…' : 'Save'}
              </button>
              <button
                type="button"
                onClick={cancel}
                className="flex-1 border border-hairline px-3 py-2 text-xs uppercase tracking-[0.1em] text-ink-dim hover:text-ink"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </CornerBracketPanel>
    </div>
  )
}
