import { useState } from "react"
import { MapPin, List } from "lucide-react"
import { Link } from "react-router-dom"
import { useListings, type ListingFilters } from "../api/listings"
import { ListingCard } from "../components/listings/ListingCard"
import { ListingFilters as Filters } from "../components/listings/ListingFilters"
import { ListingMap } from "../components/listings/ListingMap"
import { EmptyState } from "../components/shared/EmptyState"
import { SkeletonListingCard } from "../components/shared/Skeleton"
import { ErrorBoundary } from "../components/shared/ErrorBoundary"

export function FeedPage() {
  const [filters, setFilters] = useState<ListingFilters>({})
  const [highlighted, setHighlighted] = useState<number | null>(null)
  const [mobileView, setMobileView] = useState<"list" | "map">("list")
  const { data: listings = [], isLoading, isError, refetch } = useListings(filters)

  const hasFilters = Object.values(filters).some((v) => v !== undefined && v !== "")

  const handlePin = (id: number) => {
    setHighlighted(id)
    document.getElementById(`listing-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <Filters onChange={setFilters} />

      {/* Mobile tab toggle */}
      <div className="md:hidden flex border-b bg-white">
        {(["list", "map"] as const).map((v) => (
          <button key={v} onClick={() => setMobileView(v)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-sm font-medium transition
              ${mobileView === v ? "border-b-2 border-primary text-primary" : "text-gray-500"}`}>
            {v === "list" ? <><List className="w-4 h-4" /> Listings</> : <><MapPin className="w-4 h-4" /> Map</>}
          </button>
        ))}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Listing cards */}
        <div className={`${mobileView === "map" ? "hidden" : "flex"} md:flex flex-col w-full md:w-96 overflow-y-auto`}>
          {isLoading ? (
            <div className="p-3 grid grid-cols-1 gap-3">
              {Array.from({ length: 6 }).map((_, i) => <SkeletonListingCard key={i} />)}
            </div>
          ) : isError ? (
            <div className="p-8 text-center">
              <div className="text-3xl mb-3">😕</div>
              <p className="text-gray-700 font-medium mb-1">Could not load listings</p>
              <p className="text-sm text-gray-500 mb-4">Check your connection and try again.</p>
              <button onClick={() => refetch()} className="px-4 py-2 bg-primary text-white rounded-lg text-sm">Retry</button>
            </div>
          ) : listings.length === 0 ? (
            <EmptyState
              icon="🔍"
              title={hasFilters ? "No listings match your filters" : "No listings yet"}
              description={hasFilters ? "Try broadening your search or adjusting your budget." : "Check back soon — new listings are added daily."}
              action={hasFilters ? (
                <button onClick={() => setFilters({})} className="px-4 py-2 bg-primary text-white rounded-lg text-sm">
                  Clear filters
                </button>
              ) : undefined}
            />
          ) : (
            <div className="p-3 grid grid-cols-1 gap-3">
              {listings.map((l) => (
                <ListingCard key={l.id} listing={l} highlighted={highlighted === l.id} onHighlight={handlePin} />
              ))}
            </div>
          )}
        </div>

        {/* Map */}
        <div className={`${mobileView === "list" ? "hidden" : "block"} md:block flex-1`}>
          <ErrorBoundary title="Map could not load">
            <ListingMap listings={listings} onPinClick={handlePin} />
          </ErrorBoundary>
        </div>
      </div>

      {/* Saved listings link */}
      <div className="md:hidden border-t bg-white px-4 py-2 text-center">
        <Link to="/saved" className="text-sm text-primary hover:underline">View saved listings</Link>
      </div>
    </div>
  )
}
