import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { useRoommateMatches } from "../api/roommate"
import { MatchCard } from "../components/roommate/MatchCard"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"
import { EmptyState } from "../components/shared/EmptyState"

export function RoommatePage() {
  const { user } = useAuthStore()
  if (user?.role !== "student") return <Navigate to="/listings" replace />

  const { data: matches, isLoading, error } = useRoommateMatches()

  if (isLoading) return <LoadingSpinner />

  if (error) {
    const is422 = (error as Error).message.includes("422") || (error as Error).message.includes("onboarding")
    return (
      <EmptyState
        icon="📝"
        title={is422 ? "Complete onboarding first" : "Could not load matches"}
        description={is422 ? "Finish your profile to see roommate matches." : "Please try again later."}
      />
    )
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Roommate Matches</h1>
      <p className="text-sm text-gray-500 mb-6">Students with similar lifestyle preferences</p>

      {!matches || matches.length === 0 ? (
        <EmptyState
          icon="👥"
          title="No matches yet"
          description="Check back after more students join and complete their profiles."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {matches.map((m) => <MatchCard key={m.user_id} match={m} />)}
        </div>
      )}
    </div>
  )
}
