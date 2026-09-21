import type { CSSProperties } from 'react'
import type { Detection } from '../../types/api'

// Shared by DetectionOverlay (live tracking) and CaptureFrame (enrollment
// guide) so the pixel->percentage math lives in exactly one place.
export function bboxToStyle(bbox: Detection['bbox'], frameWidth: number, frameHeight: number): CSSProperties {
  return {
    left: `${(bbox[0] / frameWidth) * 100}%`,
    top: `${(bbox[1] / frameHeight) * 100}%`,
    width: `${(bbox[2] / frameWidth) * 100}%`,
    height: `${(bbox[3] / frameHeight) * 100}%`,
  }
}
