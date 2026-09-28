import { useEffect } from 'react'
import { useSelectCamera } from '../api/camera'

// Updated by AppShell on every detection event, so that whichever screen
// reclaims the camera next reopens the same device the user last had
// selected instead of always defaulting to 0.
export const lastCameraIndex: { current: number | null } = { current: 0 }

// Call this, unconditionally, from any component whose mount lifetime IS the
// "screen" that needs the physical camera (a page, or a full-screen modal).
// It claims the camera on mount and releases it on unmount.
export function useCameraOwner() {
  const selectCamera = useSelectCamera()

  useEffect(() => {
    selectCamera.mutate(lastCameraIndex.current ?? 0)
    return () => {
      selectCamera.mutate(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
