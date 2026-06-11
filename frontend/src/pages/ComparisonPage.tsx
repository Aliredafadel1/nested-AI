import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { useListings, useCompareListings } from "../api/listings"
import type { ListingCompareItem } from "../api/listings"
import { PhotoGallery } from "../components/listings/PhotoGallery"
import { Plus, X, BarChart2, Zap, Wifi, Bus, Shield, Users } from "lucide-react"

const NEIGHBOURHOODS: Record<number, string> = {
  1: "Hamra", 2: "Gemmayzeh", 3: "Achrafieh", 4: "Mar Mikhael",
  5: "Verdun", 6: "Badaro", 7: "Ras Beirut", 8: "Dekwaneh",
}

function ScoreBar({ value, max = 5 }: { value: number | null; max?: number }) {
  const pct = value ? (value / max) * 100 : 0
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-400"
  return (
    <div className="w-full bg-gray-100 rounded-full h-2">
      <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function MetricRow({ label, icon: Icon, values, highlight, format }: {
  label: string; icon: React.FC<{ className?: string }>; values: (number | null | string)[]
  highlight?: "high" | "low"; format?: (v: number) => string
}) {
  const nums = values.map((v) => (typeof v === "number" ? v : null))
  const best = highlight === "high"
    ? Math.max(...nums.filter((n): n is number => n !== null))
    : highlight === "low"
    ? Math.min(...nums.filter((n): n is number => n !== null))
    : null

  return (
    <tr className="border-b last:border-b-0">
      <td className="py-3 pr-4 text-sm text-gray-500 whitespace-nowrap">
        <span className="flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{label}</span>
      </td>
      {values.map((v, i) => {
        const isBest = best !== null && v === best
        return (
          <td key={i} className={`py-3 px-2 text-sm text-center font-medium
            ${isBest ? "text-green-700" : "text-gray-700"}`}>
            {v === null ? <span className="text-gray-300">—</span>
              : typeof v === "string" ? v
              : format ? format(v as number) : v}
            {isBest && <span className="ml-1 text-[10px] text-green-600">✓</span>}
          </td>
        )
      })}
    </tr>
  )
}

export function ComparisonPage() {
  const { user } = useAuthStore()
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [result, setResult] = useState<ListingCompareItem[] | null>(null)
  const [search, setSearch] = useState("")
  const compare = useCompareListings()

  const { data: listings = [] } = useListings()
  const filtered = listings.filter((l) =>
    l.title.toLowerCase().includes(search.toLowerCase()) ||
    (NEIGHBOURHOODS[l.neighbourhood_id] || "").toLowerCase().includes(search.toLowerCase())
  )

  if (user?.role !== "student") return <Navigate to="/listings" replace />

  const toggle = (id: number) => {
    setResult(null)
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 3 ? [...prev, id] : prev
    )
  }

  const handleCompare = () => {
    compare.mutate(selectedIds, {
      onSuccess: (data) => setResult(data.items),
    })
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        <BarChart2 className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold">Apartment Comparison</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6">Select 2–3 listings to compare side-by-side</p>

      {/* Picker */}
      {!result && (
        <div>
          {/* Selected chips */}
          {selectedIds.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {selectedIds.map((id) => {
                const l = listings.find((x) => x.id === id)
                return (
                  <div key={id} className="flex items-center gap-1.5 bg-primary/10 text-primary rounded-full px-3 py-1.5 text-sm">
                    <span className="font-medium">{l?.title.slice(0, 22)}{(l?.title.length ?? 0) > 22 ? "…" : ""}</span>
                    <button onClick={() => toggle(id)}><X className="w-3.5 h-3.5" /></button>
                  </div>
                )
              })}
              {selectedIds.length >= 2 && (
                <button
                  onClick={handleCompare}
                  disabled={compare.isPending}
                  className="flex items-center gap-1.5 bg-primary text-white rounded-full px-4 py-1.5 text-sm font-medium hover:bg-primary/90 transition disabled:opacity-60"
                >
                  {compare.isPending ? "Comparing…" : "Compare →"}
                </button>
              )}
            </div>
          )}

          {/* Search + list */}
          <input
            className="w-full border rounded-xl px-4 py-2.5 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-primary/30"
            placeholder="Search listings by name or area…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.slice(0, 30).map((l) => {
              const sel = selectedIds.includes(l.id)
              const full = selectedIds.length >= 3 && !sel
              return (
                <div
                  key={l.id}
                  role="button"
                  tabIndex={full ? -1 : 0}
                  onClick={() => !full && toggle(l.id)}
                  onKeyDown={(e) => e.key === "Enter" && !full && toggle(l.id)}
                  className={`bg-white border rounded-xl overflow-hidden transition select-none
                    ${sel ? "ring-2 ring-primary shadow-md" : "hover:shadow-sm"}
                    ${full ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
                >
                  <div className="h-28 relative pointer-events-none">
                    <PhotoGallery photos={l.photos ?? []} title={l.title} className="h-28" />
                    {sel && (
                      <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                        <div className="w-7 h-7 bg-primary rounded-full flex items-center justify-center text-white text-xs font-bold">
                          {selectedIds.indexOf(l.id) + 1}
                        </div>
                      </div>
                    )}
                    {!sel && !full && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-white/80 rounded-full flex items-center justify-center">
                        <Plus className="w-3.5 h-3.5 text-primary" />
                      </div>
                    )}
                  </div>
                  <div className="p-3">
                    <p className="text-sm font-semibold text-gray-800 line-clamp-1">{l.title}</p>
                    <p className="text-xs text-gray-500">{NEIGHBOURHOODS[l.neighbourhood_id]} · ${l.price}/mo</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Results table */}
      {result && (
        <div>
          <button
            onClick={() => setResult(null)}
            className="text-sm text-primary hover:underline mb-6"
          >
            ← Change selection
          </button>

          {/* Photo headers */}
          <div className={`grid gap-4 mb-6 ${result.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
            {result.map(({ listing, true_monthly }) => (
              <div key={listing.id} className="bg-white border rounded-xl overflow-hidden">
                <PhotoGallery photos={listing.photos ?? []} title={listing.title} className="h-36" />
                <div className="p-3">
                  <p className="font-semibold text-sm line-clamp-1">{listing.title}</p>
                  <p className="text-xs text-gray-500">{NEIGHBOURHOODS[listing.neighbourhood_id]}</p>
                  <p className="text-primary font-bold mt-1">${listing.price}<span className="text-xs text-gray-400 font-normal">/mo rent</span></p>
                  <p className="text-xs text-gray-600 mt-0.5">~${true_monthly}/mo total</p>
                </div>
              </div>
            ))}
          </div>

          {/* Comparison table */}
          <div className="bg-white border rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="py-3 px-4 text-left text-xs text-gray-500 font-medium w-32">Metric</th>
                  {result.map(({ listing }) => (
                    <th key={listing.id} className="py-3 px-2 text-xs text-gray-500 font-medium text-center">
                      {listing.title.slice(0, 18)}{listing.title.length > 18 ? "…" : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                <MetricRow label="Rent/mo" icon={({ className }) => <span className={className}>$</span>}
                  values={result.map((i) => i.listing.price)}
                  highlight="low" format={(v) => `$${v}`} />
                <MetricRow label="True monthly" icon={({ className }) => <span className={className}>$</span>}
                  values={result.map((i) => i.true_monthly)}
                  highlight="low" format={(v) => `$${v}`} />
                <MetricRow label="Bedrooms" icon={({ className }) => <span className={className}>🛏</span>}
                  values={result.map((i) => i.listing.bedrooms)}
                  highlight="high" />
                <MetricRow label="Fraud risk" icon={Shield}
                  values={result.map((i) => {
                    const s = i.listing.fraud_score ?? 0
                    return s >= 0.7 ? "High ⚠️" : s >= 0.4 ? "Medium" : "Low ✓"
                  })} />
                <MetricRow label="Electricity" icon={Zap}
                  values={result.map((i) => i.area.electricity_hours)}
                  highlight="high" format={(v) => `${v}h/day`} />
                <MetricRow label="Generator" icon={Zap}
                  values={result.map((i) => i.area.generator_cost)}
                  highlight="low" format={(v) => `$${v}/mo`} />
                <MetricRow label="Internet" icon={Wifi}
                  values={result.map((i) => i.area.internet)}
                  highlight="high" format={(v) => `${v}/5`} />
                <MetricRow label="Transport" icon={Bus}
                  values={result.map((i) => i.area.transport)}
                  highlight="high" format={(v) => `${v}/5`} />
                <MetricRow label="Safety" icon={Shield}
                  values={result.map((i) => i.area.safety)}
                  highlight="high" format={(v) => `${v}/5`} />
                <MetricRow label="Student vibe" icon={Users}
                  values={result.map((i) => i.area.student_vibe)}
                  highlight="high" format={(v) => `${v}/5`} />
                <MetricRow label="Livability" icon={BarChart2}
                  values={result.map((i) => i.area.livability_score)}
                  highlight="high" format={(v) => `${Math.round(v * 100)}%`} />
              </tbody>
            </table>
          </div>

          {/* Score bars */}
          <div className={`grid gap-4 mt-6 ${result.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
            {result.map(({ listing, area }) => (
              <div key={listing.id} className="bg-white border rounded-xl p-4 space-y-2.5">
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Area scores</p>
                {[
                  { label: "Electricity", value: area.electricity_hours, max: 24 },
                  { label: "Internet", value: area.internet, max: 5 },
                  { label: "Transport", value: area.transport, max: 5 },
                  { label: "Safety", value: area.safety, max: 5 },
                  { label: "Student vibe", value: area.student_vibe, max: 5 },
                ].map(({ label, value, max }) => (
                  <div key={label}>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>{label}</span>
                      <span>{value ?? "?"}/{max}</span>
                    </div>
                    <ScoreBar value={value} max={max} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
