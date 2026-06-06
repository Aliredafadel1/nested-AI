import { useParams, useNavigate } from "react-router-dom"
import { useState } from "react"
import { ArrowLeft, MessageSquare, Heart } from "lucide-react"
import { useListing, useSaveListing, useUnsaveListing } from "../api/listings"
import { useFraudReport } from "../api/fraud"
import { useChatStore } from "../stores/chatStore"
import { useAuthStore } from "../stores/authStore"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"
import { ListingBadge } from "../components/listings/ListingBadge"

export function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: listing, isLoading } = useListing(Number(id))
  const { data: fraud } = useFraudReport(Number(id))
  const { user } = useAuthStore()
  const { open, addMessage } = useChatStore()
  const save = useSaveListing()
  const unsave = useUnsaveListing()
  const [saved, setSaved] = useState(false)
  const [fraudOpen, setFraudOpen] = useState(false)

  if (isLoading) return <LoadingSpinner />
  if (!listing) return <div className="p-4 text-red-500">Listing not found</div>

  const askAI = () => {
    addMessage({ id: "prefill", role: "user", content: `Tell me about listing #${listing.id}: ${listing.title} in neighbourhood ${listing.neighbourhood_id}, priced at $${listing.price}/month.` })
    open()
  }

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 mb-4 hover:text-gray-700">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      <div className="bg-white rounded-2xl border overflow-hidden">
        <div className="h-64 bg-gray-100 flex items-center justify-center text-5xl">🏠</div>
        <div className="p-5">
          <div className="flex justify-between items-start mb-3">
            <h1 className="text-xl font-bold text-gray-900">{listing.title}</h1>
            <div className="text-xl font-bold text-primary">${listing.price}<span className="text-sm font-normal text-gray-400">/mo</span></div>
          </div>
          <div className="text-sm text-gray-500 mb-3">{listing.bedrooms} bedroom · Neighbourhood #{listing.neighbourhood_id}</div>
          <ListingBadge fraud_score={listing.fraud_score} />
          {listing.description && <p className="mt-4 text-sm text-gray-700 leading-relaxed">{listing.description}</p>}

          <div className="flex gap-3 mt-6">
            {user?.role === "student" && (
              <>
                <button onClick={() => { saved ? unsave.mutate(listing.id) : save.mutate(listing.id); setSaved(!saved) }}
                  className={`flex items-center gap-2 px-4 py-2.5 border rounded-xl text-sm
                    ${saved ? "bg-red-50 border-red-200 text-red-600" : "hover:bg-gray-50"}`}>
                  <Heart className={`w-4 h-4 ${saved ? "fill-current" : ""}`} />
                  {saved ? "Saved" : "Save"}
                </button>
                <button onClick={askAI}
                  className="flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-xl text-sm">
                  <MessageSquare className="w-4 h-4" /> Ask AI
                </button>
              </>
            )}
          </div>

          {fraud && (
            <div className="mt-4">
              <button onClick={() => setFraudOpen(!fraudOpen)}
                className="text-xs text-gray-400 hover:text-gray-600 underline">
                {fraudOpen ? "Hide" : "Show"} fraud report (score: {fraud.score.toFixed(2)})
              </button>
              {fraudOpen && (
                <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-gray-600 space-y-1">
                  {Object.entries(fraud.evidence).map(([k, flags]) =>
                    (flags as string[]).length > 0 && <p key={k}><strong>{k}:</strong> {(flags as string[]).join(", ")}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
