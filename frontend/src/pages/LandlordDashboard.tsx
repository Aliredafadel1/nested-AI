import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { useListings, useListingStats, useCreateListing, type Listing } from "../api/listings"
import { useCalculateCost } from "../api/estimator"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"
import { EmptyState } from "../components/shared/EmptyState"
import { Plus } from "lucide-react"

const HOODS = [
  { id: 1, name: "Hamra" }, { id: 2, name: "Gemmayzeh" }, { id: 3, name: "Achrafieh" },
  { id: 4, name: "Mar Mikhael" }, { id: 5, name: "Verdun" }, { id: 6, name: "Badaro" },
  { id: 7, name: "Ras Beirut" }, { id: 8, name: "Dekwaneh" },
]

function ListingRow({ listing }: { listing: Listing }) {
  const { data: stats } = useListingStats(listing.id)
  return (
    <tr className="border-b hover:bg-gray-50">
      <td className="px-4 py-3 text-sm font-medium">{listing.title}</td>
      <td className="px-4 py-3 text-sm">${listing.price}</td>
      <td className="px-4 py-3 text-sm">{listing.bedrooms} bd</td>
      <td className="px-4 py-3 text-sm text-center">{stats?.saved_count ?? "—"}</td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full ${listing.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
          {listing.status}
        </span>
      </td>
    </tr>
  )
}

export function LandlordDashboard() {
  const { user } = useAuthStore()
  const { data: listings = [], isLoading } = useListings()
  const createListing = useCreateListing()
  const calcCost = useCalculateCost()
  const [showNew, setShowNew] = useState(false)
  const [newData, setNewData] = useState({ title: "", price: 500, bedrooms: 1, neighbourhood_id: 1, description: "" })
  const [estRent, setEstRent] = useState(500)
  const [estHood, setEstHood] = useState(1)

  if (user?.role !== "landlord") return <Navigate to="/listings" replace />

  const myListings = listings

  const submit = () => {
    createListing.mutate(newData, { onSuccess: () => setShowNew(false) })
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold">My Listings</h1>
        <button onClick={() => setShowNew(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm">
          <Plus className="w-4 h-4" /> New Listing
        </button>
      </div>

      {showNew && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <h2 className="font-semibold text-sm">New Listing</h2>
          <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Title" value={newData.title} onChange={(e) => setNewData({ ...newData, title: e.target.value })} />
          <div className="flex gap-3">
            <input type="number" className="flex-1 border rounded-lg px-3 py-2 text-sm" placeholder="Price (USD)" value={newData.price} onChange={(e) => setNewData({ ...newData, price: Number(e.target.value) })} />
            <input type="number" className="flex-1 border rounded-lg px-3 py-2 text-sm" placeholder="Bedrooms" value={newData.bedrooms} onChange={(e) => setNewData({ ...newData, bedrooms: Number(e.target.value) })} />
          </div>
          <select className="w-full border rounded-lg px-3 py-2 text-sm" value={newData.neighbourhood_id} onChange={(e) => setNewData({ ...newData, neighbourhood_id: Number(e.target.value) })}>
            {HOODS.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
          <textarea className="w-full border rounded-lg px-3 py-2 text-sm" rows={3} placeholder="Description" value={newData.description} onChange={(e) => setNewData({ ...newData, description: e.target.value })} />
          <div className="flex gap-2">
            <button onClick={submit} disabled={createListing.isPending} className="px-4 py-2 bg-primary text-white rounded-lg text-sm disabled:opacity-60">
              {createListing.isPending ? "Creating…" : "Create"}
            </button>
            <button onClick={() => setShowNew(false)} className="px-4 py-2 border rounded-lg text-sm">Cancel</button>
          </div>
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : myListings.length === 0 ? (
        <EmptyState icon="🏠" title="No listings yet" description="Create your first listing to get started." />
      ) : (
        <div className="bg-white rounded-xl border overflow-x-auto">
          <table className="w-full min-w-[500px]">
            <thead><tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase">
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3">Beds</th>
              <th className="px-4 py-3 text-center">Inquiries</th>
              <th className="px-4 py-3">Status</th>
            </tr></thead>
            <tbody>{myListings.map((l) => <ListingRow key={l.id} listing={l} />)}</tbody>
          </table>
        </div>
      )}

      {/* Cost Estimator */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="font-semibold mb-4">Monthly Cost Estimator</h2>
        <div className="flex gap-3 mb-4">
          <input type="number" className="flex-1 border rounded-lg px-3 py-2 text-sm" placeholder="Rent (USD)" value={estRent} onChange={(e) => setEstRent(Number(e.target.value))} />
          <select className="flex-1 border rounded-lg px-3 py-2 text-sm" value={estHood} onChange={(e) => setEstHood(Number(e.target.value))}>
            {HOODS.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
          <button onClick={() => calcCost.mutate({ rent: estRent, neighbourhood_id: estHood })}
            disabled={calcCost.isPending}
            className="px-4 py-2 bg-primary text-white rounded-lg text-sm disabled:opacity-60">
            {calcCost.isPending ? "…" : "Calculate"}
          </button>
        </div>
        {calcCost.data && (
          <table className="w-full text-sm">
            <tbody>
              {[["Rent", calcCost.data.rent], ["Generator", calcCost.data.generator], ["Water", calcCost.data.water],
                ["Internet", calcCost.data.internet], ["Transport", calcCost.data.transport]].map(([label, val]) => (
                <tr key={label as string} className="border-b">
                  <td className="py-2 text-gray-600">{label}</td>
                  <td className="py-2 text-right font-medium">${val}</td>
                </tr>
              ))}
              <tr className="bg-gray-50">
                <td className="py-2 font-bold">Total Monthly</td>
                <td className="py-2 text-right font-bold text-primary">${calcCost.data.total_monthly}</td>
              </tr>
              {calcCost.data.commute_minutes !== null && (
                <tr>
                  <td className="py-2 text-gray-500 text-xs">Est. commute</td>
                  <td className="py-2 text-right text-xs text-gray-500">{calcCost.data.commute_minutes} min</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
