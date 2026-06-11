import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { Navigate, Link } from "react-router-dom"
import { useRoommateMatches, useMyRequests, useRespondToRequest } from "../api/roommate"
import { MatchCard } from "../components/roommate/MatchCard"
import { MessageThread } from "../components/roommate/MessageThread"
import { SkeletonMatchCard } from "../components/shared/Skeleton"
import { EmptyState } from "../components/shared/EmptyState"
import { Check, X, MessageCircle } from "lucide-react"

type Tab = "matches" | "requests"

const STATUS_COLOR: Record<string, string> = {
  pending: "text-yellow-600 bg-yellow-50",
  accepted: "text-green-700 bg-green-50",
  declined: "text-red-600 bg-red-50",
}

export function RoommatePage() {
  const { user } = useAuthStore()
  const [tab, setTab] = useState<Tab>("matches")
  const [openThread, setOpenThread] = useState<{ requestId: number; otherId: number } | null>(null)

  const { data: matches, isLoading: matchLoading, error } = useRoommateMatches()
  const { data: requests = [], isLoading: reqLoading } = useMyRequests()
  const respond = useRespondToRequest()

  if (user?.role !== "student") return <Navigate to="/listings" replace />

  const myId = user.id
  const pendingIncoming = requests.filter((r) => r.to_user_id === myId && r.status === "pending")
  const inboxBadge = pendingIncoming.length

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Roommate Finder</h1>
      <p className="text-sm text-gray-500 mb-4">Find and connect with compatible housemates</p>

      {/* Tabs */}
      <div className="flex border-b mb-6">
        <button
          onClick={() => setTab("matches")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition
            ${tab === "matches" ? "border-primary text-primary" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          Matches
        </button>
        <button
          onClick={() => setTab("requests")}
          className={`relative px-4 py-2.5 text-sm font-medium border-b-2 transition
            ${tab === "requests" ? "border-primary text-primary" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          Requests & Messages
          {inboxBadge > 0 && (
            <span className="ml-1.5 px-1.5 py-0.5 bg-red-500 text-white text-xs rounded-full">
              {inboxBadge}
            </span>
          )}
        </button>
      </div>

      {/* Matches tab */}
      {tab === "matches" && (
        <>
          {matchLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => <SkeletonMatchCard key={i} />)}
            </div>
          )}
          {error && (() => {
            const is422 = (error as Error).message.includes("422") || (error as Error).message.includes("onboarding")
            return (
              <EmptyState
                icon={is422 ? "📝" : "⚠️"}
                title={is422 ? "Profile not ready yet" : "Could not load matches"}
                description={is422
                  ? "Set your preferences so we can find compatible roommates."
                  : "Please try again later."}
                action={is422 ? (
                  <Link to="/onboarding" className="inline-block px-6 py-2.5 bg-primary text-white rounded-xl text-sm font-medium">
                    Complete your profile →
                  </Link>
                ) : undefined}
              />
            )
          })()}
          {!matchLoading && !error && (!matches || matches.length === 0) && (
            <EmptyState
              icon="👥"
              title="No matches yet"
              description="Check back after more students join and complete their profiles."
              action={
                <Link to="/onboarding" className="inline-block px-4 py-2 bg-primary text-white rounded-lg text-sm">
                  Update your profile
                </Link>
              }
            />
          )}
          {!matchLoading && !error && matches && matches.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {matches.map((m) => <MatchCard key={m.user_id} match={m} />)}
            </div>
          )}
        </>
      )}

      {/* Requests & Messages tab */}
      {tab === "requests" && (
        <div className="space-y-3">
          {reqLoading && (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />)}
            </div>
          )}
          {!reqLoading && requests.length === 0 && (
            <EmptyState
              icon="💬"
              title="No requests yet"
              description="Send a roommate request from the Matches tab to start a conversation."
            />
          )}
          {requests.map((req) => {
            const isIncoming = req.to_user_id === myId
            const otherId = isIncoming ? req.from_user_id : req.to_user_id

            return (
              <div key={req.id} className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold text-sm shrink-0">
                      {otherId}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-800">Student #{otherId}</p>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${STATUS_COLOR[req.status] ?? ""}`}>
                          {req.status}
                        </span>
                        <span className="text-xs text-gray-400">{isIncoming ? "incoming" : "outgoing"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {/* Accept/decline for incoming pending */}
                    {isIncoming && req.status === "pending" && (
                      <>
                        <button
                          onClick={() => respond.mutate({ requestId: req.id, accept: true })}
                          disabled={respond.isPending}
                          className="min-w-[36px] min-h-[36px] flex items-center justify-center bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition"
                          title="Accept"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => respond.mutate({ requestId: req.id, accept: false })}
                          disabled={respond.isPending}
                          className="min-w-[36px] min-h-[36px] flex items-center justify-center bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition"
                          title="Decline"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </>
                    )}

                    {/* Open thread for accepted */}
                    {req.status === "accepted" && (
                      <button
                        onClick={() => setOpenThread({ requestId: req.id, otherId })}
                        className="flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-xs rounded-lg hover:bg-primary/90 transition"
                      >
                        <MessageCircle className="w-3.5 h-3.5" />
                        Chat
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Message thread drawer */}
      {openThread && (
        <MessageThread
          requestId={openThread.requestId}
          otherUserId={openThread.otherId}
          onClose={() => setOpenThread(null)}
        />
      )}
    </div>
  )
}
