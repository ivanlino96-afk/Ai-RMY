import { useRef, useState } from 'react'
import type { ChangeEvent } from 'react'

interface PhotoUploaderProps {
  onSelect: (file: File | null) => void
}

export function PhotoUploader({ onSelect }: PhotoUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    onSelect(file)
    setPreviewUrl(file ? URL.createObjectURL(file) : null)
  }

  return (
    <button
      type="button"
      onClick={() => inputRef.current?.click()}
      className="flex aspect-square w-full items-center justify-center border border-dashed border-hairline bg-void text-xs uppercase tracking-[0.1em] text-ink-dim hover:border-lock hover:text-lock"
    >
      {previewUrl ? (
        <img src={previewUrl} alt="Selected photo" className="h-full w-full object-cover" />
      ) : (
        'Select photo'
      )}
      <input ref={inputRef} type="file" accept="image/*" onChange={handleChange} className="hidden" />
    </button>
  )
}
