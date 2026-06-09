import { useAuthStore } from "../stores/authStore"
import { Navigate, Link } from "react-router-dom"
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
    const is422 = (error as Error).message.includes("422") || (error as Error).message.includes("onboarding") || (error as Error).message.includes("embedding")
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-4">{is422 ? "📝" : "⚠️"}</div>
        <h2 className="text-lg font-semibold mb-2">{is422 ? "Profile not ready yet" : "Could not load matches"}</h2>
        <p className="text-sm text-gray-500 mb-6">
          {is422
            ? "Set your preferences so we can find compatible roommates for you."
            : "Please try again later."}
        </p>
        {is422 && (
          <Link
            to="/onboarding"
            className="inline-block px-6 py-2.5 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary/90 transition"
          >
            Complete your profile →
          </Link>
        )}
      </div>
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
