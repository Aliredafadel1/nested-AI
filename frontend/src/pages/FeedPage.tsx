import { useState } from "react"
import { MapPin, List } from "lucide-react"
import { useListings, type ListingFilters } from "../api/listings"
import { ListingCard } from "../components/listings/ListingCard"
import { ListingFilters as Filters } from "../components/listings/ListingFilters"
import { ListingMap } from "../components/listings/ListingMap"
import { EmptyState } from "../components/shared/EmptyState"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"
import { ErrorBoundary } from "../components/shared/ErrorBoundary"

export function FeedPage() {
  const [filters, setFilters] = useState<ListingFilters>({})
  const [highlighted, setHighlighted] = useState<number | null>(null)
  const [mobileView, setMobileView] = useState<"list" | "map">("list")
  const { data: listings = [], isLoading, isError, refetch } = useListings(filters)

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
          {isLoading ? <LoadingSpinner /> :
           isError ? (
            <div className="p-4 text-center">
              <p className="text-red-500 text-sm mb-2">Failed to load listings</p>
              <button onClick={() => refetch()} className="text-sm text-primary hover:underline">Retry</button>
            </div>
           ) : listings.length === 0 ? (
            <EmptyState title="No listings match your filters" description="Try broadening your search area or adjusting your budget." />
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
          <ErrorBoundary>
            <ListingMap listings={listings} onPinClick={handlePin} />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  )
}
