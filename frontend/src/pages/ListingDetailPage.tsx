import { useParams, useNavigate } from "react-router-dom"
import { useState, Suspense, lazy } from "react"
import { ArrowLeft, MessageSquare, Heart, Clock, MapPin } from "lucide-react"
import { useListing, useListings, useSaveListing, useUnsaveListing } from "../api/listings"
import { useFraudReport } from "../api/fraud"
import { useCommute } from "../api/estimator"
import { useMe } from "../api/users"
import { useChatStore } from "../stores/chatStore"
import { useAuthStore } from "../stores/authStore"
import { SkeletonListingDetail } from "../components/shared/Skeleton"
import { ListingBadge } from "../components/listings/ListingBadge"
import { PhotoGallery } from "../components/listings/PhotoGallery"
import { ListingCard } from "../components/listings/ListingCard"
import { ErrorBoundary } from "../components/shared/ErrorBoundary"

const ListingMiniMap = lazy(() =>
  import("../components/listings/ListingMiniMap").then((m) => ({ default: m.ListingMiniMap }))
)

const NEIGHBOURHOODS: Record<number, string> = {
  1: "Hamra", 2: "Gemmayzeh", 3: "Achrafieh", 4: "Mar Mikhael",
  5: "Verdun", 6: "Badaro", 7: "Ras Beirut", 8: "Dekwaneh",
}

export function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: listing, isLoading, isError } = useListing(Number(id))
  const { data: fraud } = useFraudReport(Number(id))
  const { user } = useAuthStore()
  const { data: me } = useMe()
  const { open, addMessage } = useChatStore()
  const save = useSaveListing()
  const unsave = useUnsaveListing()
  const [saved, setSaved] = useState(false)
  const [fraudOpen, setFraudOpen] = useState(false)

  const universityId = me?.profile && "university_id" in me.profile ? (me.profile as { university_id?: number | null }).university_id : null
  const { data: commute } = useCommute(listing?.price ?? 0, listing?.neighbourhood_id ?? 0, universityId)

  const { data: neighbourhoodListings } = useListings(
    listing ? { neighbourhood_id: listing.neighbourhood_id } : {}
  )
  const similar = neighbourhoodListings?.filter((l) => l.id !== listing?.id).slice(0, 3) ?? []

  if (isLoading) return <SkeletonListingDetail />

  if (isError || !listing) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="text-4xl mb-4">🏚️</div>
        <h2 className="text-lg font-semibold text-gray-700 mb-2">Listing not found</h2>
        <p className="text-sm text-gray-500 mb-6">This listing may have been removed or is no longer available.</p>
        <button onClick={() => navigate("/listings")} className="px-4 py-2 bg-primary text-white rounded-lg text-sm">
          Back to listings
        </button>
      </div>
    )
  }

  const askAI = () => {
    addMessage({ id: "prefill", role: "user", content: `Tell me about listing #${listing.id}: ${listing.title} in ${NEIGHBOURHOODS[listing.neighbourhood_id] ?? "Beirut"}, priced at $${listing.price}/month.` })
    open()
  }

  return (
    <div className="max-w-2xl mx-auto pb-12">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 mb-4 hover:text-gray-700">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      <div className="bg-white rounded-2xl border overflow-hidden">
        {/* Photo gallery */}
        <PhotoGallery
          photos={listing.photos ?? []}
          title={listing.title}
          className="h-72 md:h-80"
        />

        <div className="p-5">
          {/* Title + price */}
          <div className="flex justify-between items-start mb-3">
            <h1 className="text-xl font-bold text-gray-900 pr-4">{listing.title}</h1>
            <div className="text-xl font-bold text-primary shrink-0">
              ${listing.price}<span className="text-sm font-normal text-gray-400">/mo</span>
            </div>
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500 mb-3">
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              {NEIGHBOURHOODS[listing.neighbourhood_id] ?? "Beirut"}
            </span>
            <span>{listing.bedrooms} bedroom{listing.bedrooms !== 1 ? "s" : ""}</span>
            {commute?.commute_minutes != null && (
              <span className="flex items-center gap-1 text-emerald-600 font-medium">
                <Clock className="w-3.5 h-3.5" />
                {commute.commute_minutes} min to campus
              </span>
            )}
          </div>

          <ListingBadge fraud_score={listing.fraud_score} />

          {listing.description && (
            <p className="mt-4 text-sm text-gray-700 leading-relaxed">{listing.description}</p>
          )}

          {/* Amenities */}
          {listing.amenities && Object.keys(listing.amenities).length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {Object.entries(listing.amenities)
                .filter(([, v]) => v)
                .map(([k]) => (
                  <span key={k} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs capitalize">
                    {k.replace(/_/g, " ")}
                  </span>
                ))}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 mt-6">
            {user?.role === "student" && (
              <>
                <button
                  onClick={() => { saved ? unsave.mutate(listing.id) : save.mutate(listing.id); setSaved(!saved) }}
                  className={`flex items-center gap-2 px-4 py-2.5 border rounded-xl text-sm min-h-[44px]
                    ${saved ? "bg-red-50 border-red-200 text-red-600" : "hover:bg-gray-50"}`}
                >
                  <Heart className={`w-4 h-4 ${saved ? "fill-current" : ""}`} />
                  {saved ? "Saved" : "Save"}
                </button>
                <button
                  onClick={askAI}
                  className="flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-xl text-sm min-h-[44px]"
                >
                  <MessageSquare className="w-4 h-4" /> Ask AI
                </button>
              </>
            )}
          </div>

          {/* Fraud report */}
          {fraud && (
            <div className="mt-4">
              <button
                onClick={() => setFraudOpen(!fraudOpen)}
                className="text-xs text-gray-400 hover:text-gray-600 underline"
              >
                {fraudOpen ? "Hide" : "Show"} fraud report (score: {fraud.score.toFixed(2)})
              </button>
              {fraudOpen && (
                <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-gray-600 space-y-1">
                  {Object.entries(fraud.evidence).map(([k, flags]) =>
                    (flags as string[]).length > 0 && (
                      <p key={k}><strong>{k}:</strong> {(flags as string[]).join(", ")}</p>
                    )
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      {listing.lat && listing.lng && (
        <div className="mt-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Location</h2>
          <ErrorBoundary title="Map could not load">
            <Suspense fallback={<div className="h-48 bg-gray-100 rounded-xl animate-pulse" />}>
              <ListingMiniMap lat={listing.lat} lng={listing.lng} title={listing.title} />
            </Suspense>
          </ErrorBoundary>
        </div>
      )}

      {/* Similar listings */}
      {similar.length > 0 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            More in {NEIGHBOURHOODS[listing.neighbourhood_id] ?? "this area"}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {similar.map((l) => (
              <ListingCard key={l.id} listing={l} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
