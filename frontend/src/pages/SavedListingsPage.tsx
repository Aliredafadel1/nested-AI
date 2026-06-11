import { Link } from "react-router-dom"
import { useSavedListings } from "../api/listings"
import { ListingCard } from "../components/listings/ListingCard"
import { SkeletonListingCard } from "../components/shared/Skeleton"
import { EmptyState } from "../components/shared/EmptyState"

export function SavedListingsPage() {
  const { data: listings, isLoading, isError, refetch } = useSavedListings()

  if (isLoading) {
    return (
      <div>
        <div className="h-7 w-40 bg-gray-200 rounded animate-pulse mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonListingCard key={i} />)}
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <EmptyState
        icon="⚠️"
        title="Could not load saved listings"
        description="Check your connection and try again."
        action={<button onClick={() => refetch()} className="px-4 py-2 bg-primary text-white rounded-lg text-sm">Retry</button>}
      />
    )
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">Saved Listings</h1>
      {!listings || listings.length === 0 ? (
        <EmptyState
          icon="❤️"
          title="No saved listings yet"
          description="Tap the heart on any listing to save it here for later."
          action={
            <Link to="/listings" className="inline-block px-4 py-2 bg-primary text-white rounded-lg text-sm">
              Browse listings
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {listings.map((l) => (
            <ListingCard key={l.id} listing={l} saved />
          ))}
        </div>
      )}
    </div>
  )
}
