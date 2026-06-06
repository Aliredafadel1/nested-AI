import { useState } from "react"
import type { ListingFilters } from "../../api/listings"

const HOODS = [
  { id: 1, name: "Hamra" }, { id: 2, name: "Gemmayzeh" }, { id: 3, name: "Achrafieh" },
  { id: 4, name: "Mar Mikhael" }, { id: 5, name: "Verdun" }, { id: 6, name: "Badaro" },
  { id: 7, name: "Ras Beirut" }, { id: 8, name: "Dekwaneh" },
]

interface Props { onChange: (f: ListingFilters) => void }

export function ListingFilters({ onChange }: Props) {
  const [f, setF] = useState<ListingFilters>({})
  const update = (patch: Partial<ListingFilters>) => {
    const next = { ...f, ...patch }
    setF(next); onChange(next)
  }

  return (
    <div className="flex flex-wrap gap-2 p-3 bg-white border-b">
      <select
        className="text-sm border rounded-lg px-3 py-1.5"
        value={f.neighbourhood_id ?? ""}
        onChange={(e) => update({ neighbourhood_id: e.target.value ? Number(e.target.value) : undefined })}
      >
        <option value="">All Areas</option>
        {HOODS.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
      </select>
      <input
        type="number" placeholder="Min $" className="text-sm border rounded-lg px-3 py-1.5 w-24"
        onChange={(e) => update({ min_price: e.target.value ? Number(e.target.value) : undefined })}
      />
      <input
        type="number" placeholder="Max $" className="text-sm border rounded-lg px-3 py-1.5 w-24"
        onChange={(e) => update({ max_price: e.target.value ? Number(e.target.value) : undefined })}
      />
      <select
        className="text-sm border rounded-lg px-3 py-1.5"
        value={f.bedrooms ?? ""}
        onChange={(e) => update({ bedrooms: e.target.value ? Number(e.target.value) : undefined })}
      >
        <option value="">Any beds</option>
        <option value="1">1 bed</option>
        <option value="2">2 beds</option>
        <option value="3">3+ beds</option>
      </select>
    </div>
  )
}
