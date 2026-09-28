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

// A fixed-size square centered on a detection's bbox center, used by the
// centering reticle (distinct from the detection's own bbox outline).
export function centerBoxStyle(
  bbox: Detection['bbox'],
  boxFraction: number,
  frameWidth: number,
  frameHeight: number,
): CSSProperties {
  const cx = bbox[0] + bbox[2] / 2
  const cy = bbox[1] + bbox[3] / 2
  const w = frameWidth * boxFraction
  const h = frameHeight * boxFraction
  return {
    left: `${((cx - w / 2) / frameWidth) * 100}%`,
    top: `${((cy - h / 2) / frameHeight) * 100}%`,
    width: `${(w / frameWidth) * 100}%`,
    height: `${(h / frameHeight) * 100}%`,
  }
}
