import { useNavigate } from "react-router-dom"
import { Heart } from "lucide-react"
import { ListingBadge } from "./ListingBadge"
import type { Listing } from "../../api/listings"
import { useSaveListing, useUnsaveListing } from "../../api/listings"
import { useAuthStore } from "../../stores/authStore"
import { useState } from "react"

const NEIGHBOURHOODS: Record<number, string> = {
  1: "Hamra", 2: "Gemmayzeh", 3: "Achrafieh", 4: "Mar Mikhael",
  5: "Verdun", 6: "Badaro", 7: "Ras Beirut", 8: "Dekwaneh",
}

interface Props { listing: Listing; highlighted?: boolean; onHighlight?: (id: number) => void; saved?: boolean }

export function ListingCard({ listing, highlighted, saved: initSaved }: Props) {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [isSaved, setIsSaved] = useState(initSaved ?? false)
  const saveMut = useSaveListing()
  const unsaveMut = useUnsaveListing()

  const photoUrl = listing.photos?.[0]
    ? `http://localhost:9000/listing-photos/${listing.photos[0].minio_key}`
    : null

  const toggleSave = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (isSaved) { unsaveMut.mutate(listing.id); setIsSaved(false) }
    else { saveMut.mutate(listing.id); setIsSaved(true) }
  }

  return (
    <div
      data-highlighted={highlighted || undefined}
      className={`bg-white rounded-xl border cursor-pointer hover:shadow-md transition-shadow
        ${highlighted ? "ring-2 ring-primary shadow-md" : "border-gray-200"}`}
      onClick={() => navigate(`/listings/${listing.id}`)}
      id={`listing-${listing.id}`}
    >
      <div className="relative h-40 bg-gray-100 rounded-t-xl overflow-hidden">
        {photoUrl ? (
          <img src={photoUrl} alt={listing.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-3xl">🏠</div>
        )}
        {user?.role === "student" && (
          <button
            onClick={toggleSave}
            className="absolute top-2 right-2 p-1.5 bg-white/80 rounded-full hover:bg-white"
          >
            <Heart className={`w-4 h-4 ${isSaved ? "fill-red-500 text-red-500" : "text-gray-400"}`} />
          </button>
        )}
      </div>
      <div className="p-3">
        <div className="flex justify-between items-start mb-1">
          <h3 className="font-semibold text-sm text-gray-900 line-clamp-1">{listing.title}</h3>
          <span className="text-primary font-bold text-sm ml-2 shrink-0">${listing.price}/mo</span>
        </div>
        <p className="text-xs text-gray-500 mb-2">
          {listing.bedrooms} bed · {NEIGHBOURHOODS[listing.neighbourhood_id] || "Beirut"}
        </p>
        <ListingBadge fraud_score={listing.fraud_score} />
      </div>
    </div>
  )
}
