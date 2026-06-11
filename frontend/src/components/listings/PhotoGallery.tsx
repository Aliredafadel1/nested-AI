import { useState, useRef } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

const MINIO_BASE = "http://localhost:9000/listing-photos"

interface Props {
  photos: { minio_key: string; is_primary: boolean }[]
  title: string
  className?: string
}

export function PhotoGallery({ photos, title, className = "" }: Props) {
  const [current, setCurrent] = useState(0)
  const touchStartX = useRef<number | null>(null)

  if (!photos.length) {
    return (
      <div className={`bg-gray-100 flex items-center justify-center text-gray-400 text-4xl ${className}`}>
        🏠
      </div>
    )
  }

  const prev = (e: React.MouseEvent) => {
    e.stopPropagation()
    setCurrent((c) => (c - 1 + photos.length) % photos.length)
  }
  const next = (e: React.MouseEvent) => {
    e.stopPropagation()
    setCurrent((c) => (c + 1) % photos.length)
  }
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
  }
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return
    const diff = touchStartX.current - e.changedTouches[0].clientX
    if (Math.abs(diff) > 40) {
      if (diff > 0) setCurrent((c) => (c + 1) % photos.length)
      else setCurrent((c) => (c - 1 + photos.length) % photos.length)
    }
    touchStartX.current = null
  }

  return (
    <div
      className={`relative overflow-hidden select-none ${className}`}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <img
        src={`${MINIO_BASE}/${photos[current].minio_key}`}
        alt={`${title} — photo ${current + 1}`}
        className="w-full h-full object-cover"
        loading="lazy"
      />

      {/* Prev / next — desktop only, shown on hover via group */}
      {photos.length > 1 && (
        <>
          <button
            onClick={prev}
            className="hidden md:flex absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 bg-black/40 hover:bg-black/60 text-white rounded-full items-center justify-center transition"
            aria-label="Previous photo"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={next}
            className="hidden md:flex absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 bg-black/40 hover:bg-black/60 text-white rounded-full items-center justify-center transition"
            aria-label="Next photo"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </>
      )}

      {/* Dot indicators */}
      {photos.length > 1 && (
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
          {photos.map((_, i) => (
            <button
              key={i}
              onClick={(e) => { e.stopPropagation(); setCurrent(i) }}
              aria-label={`Photo ${i + 1}`}
              className={`h-1.5 rounded-full transition-all ${
                i === current ? "w-4 bg-white" : "w-1.5 bg-white/60"
              }`}
            />
          ))}
        </div>
      )}

      {/* Count badge */}
      {photos.length > 1 && (
        <div className="absolute top-2 left-2 bg-black/40 text-white text-xs px-1.5 py-0.5 rounded-full">
          {current + 1} / {photos.length}
        </div>
      )}
    </div>
  )
}
