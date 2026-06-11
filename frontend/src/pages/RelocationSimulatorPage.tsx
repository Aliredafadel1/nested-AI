import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { useSimulate } from "../api/estimator"
import type { SimulateOut } from "../api/estimator"
import { useMe } from "../api/users"
import { MapPin, Zap, Clock, DollarSign } from "lucide-react"

const NEIGHBOURHOODS: { id: number; name: string }[] = [
  { id: 1, name: "Hamra" }, { id: 2, name: "Gemmayzeh" }, { id: 3, name: "Achrafieh" },
  { id: 4, name: "Mar Mikhael" }, { id: 5, name: "Verdun" }, { id: 6, name: "Badaro" },
  { id: 7, name: "Ras Beirut" }, { id: 8, name: "Dekwaneh" },
]

const UNIVERSITIES: { id: number; name: string }[] = [
  { id: 1, name: "AUB" }, { id: 2, name: "LAU Beirut" }, { id: 3, name: "USJ" },
  { id: 4, name: "NDU" }, { id: 5, name: "LIU Beirut" }, { id: 6, name: "BAU" },
  { id: 7, name: "USEK" }, { id: 8, name: "Balamand" }, { id: 9, name: "HU Beirut" },
  { id: 10, name: "RHU" },
]

function ScoreRing({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100)
  const color = pct >= 70 ? "text-green-600" : pct >= 45 ? "text-yellow-600" : "text-red-500"
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`text-2xl font-bold ${color}`}>{pct}%</div>
      <div className="text-xs text-gray-500 text-center">{label}</div>
    </div>
  )
}

function ScoreBar({ value, max = 5, label }: { value: number | null; max?: number; label: string }) {
  const pct = value ? (value / max) * 100 : 0
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-400"
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-24 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-600 w-8 text-right">{value ?? "?"}/{max}</span>
    </div>
  )
}

const FEASIBILITY_STYLE: Record<string, string> = {
  comfortable: "bg-green-50 text-green-700 border-green-200",
  tight: "bg-yellow-50 text-yellow-700 border-yellow-200",
  "over budget": "bg-red-50 text-red-600 border-red-200",
}

const FEASIBILITY_LABEL: Record<string, string> = {
  comfortable: "Budget comfortable ✓",
  tight: "Budget tight — expect extras",
  "over budget": "Over budget with living costs",
}

interface SimResult { neighbourhood_id: number; data: SimulateOut }

export function RelocationSimulatorPage() {
  const { user } = useAuthStore()
  const { data: me } = useMe()
  const simulate = useSimulate()

  const [neighbourhoodId, setNeighbourhoodId] = useState<number>(1)
  const [budget, setBudget] = useState<number>(600)
  const [universityId, setUniversityId] = useState<number | null>(null)
  const [results, setResults] = useState<SimResult[]>([])

  if (user?.role !== "student") return <Navigate to="/listings" replace />

  const profileUniId = me?.profile && "university_id" in me.profile
    ? (me.profile as { university_id?: number | null }).university_id
    : null

  const handleSimulate = () => {
    simulate.mutate(
      { neighbourhood_id: neighbourhoodId, budget, university_id: universityId ?? profileUniId },
      {
        onSuccess: (data) => {
          setResults((prev) => {
            const existing = prev.findIndex((r) => r.neighbourhood_id === neighbourhoodId)
            if (existing >= 0) {
              const updated = [...prev]; updated[existing] = { neighbourhood_id: neighbourhoodId, data }; return updated
            }
            return [...prev, { neighbourhood_id: neighbourhoodId, data }]
          })
        },
      }
    )
  }

  const removeResult = (id: number) => setResults((prev) => prev.filter((r) => r.neighbourhood_id !== id))

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        <MapPin className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold">Relocation Simulator</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Simulate the true cost and lifestyle of living in any Beirut neighbourhood
      </p>

      {/* Input form */}
      <div className="bg-white border rounded-2xl p-5 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Neighbourhood</label>
            <select
              className="w-full border rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={neighbourhoodId}
              onChange={(e) => setNeighbourhoodId(Number(e.target.value))}
            >
              {NEIGHBOURHOODS.map((n) => (
                <option key={n.id} value={n.id}>{n.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Monthly rent budget ($)</label>
            <input
              type="number"
              min={100} max={5000} step={50}
              className="w-full border rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">
              University {profileUniId && !universityId ? "(from profile)" : ""}
            </label>
            <select
              className="w-full border rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={universityId ?? ""}
              onChange={(e) => setUniversityId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">No commute</option>
              {UNIVERSITIES.map((u) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={handleSimulate}
          disabled={simulate.isPending}
          className="mt-4 w-full sm:w-auto px-6 py-2.5 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary/90 transition disabled:opacity-60"
        >
          {simulate.isPending ? "Simulating…" : "Run Simulation →"}
        </button>
      </div>

      {/* Results */}
      {results.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <MapPin className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Pick a neighbourhood and run the simulation to see your true living costs</p>
        </div>
      )}

      <div className="space-y-6">
        {results.map(({ neighbourhood_id, data }) => (
          <div key={neighbourhood_id} className="bg-white border rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-primary px-5 py-4 text-white flex justify-between items-start">
              <div>
                <h2 className="text-lg font-bold">{data.neighbourhood_name}</h2>
                {data.neighbourhood_name_ar && (
                  <p className="text-sm opacity-75" dir="rtl">{data.neighbourhood_name_ar}</p>
                )}
              </div>
              <button
                onClick={() => removeResult(neighbourhood_id)}
                className="text-white/70 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left: scores + commute */}
              <div className="space-y-5">
                {/* Fit + feasibility */}
                <div className="flex items-center gap-6">
                  <ScoreRing value={data.fit_score} label="Student fit" />
                  <div className={`flex-1 px-3 py-2 rounded-lg border text-sm font-medium ${FEASIBILITY_STYLE[data.budget_feasibility]}`}>
                    {FEASIBILITY_LABEL[data.budget_feasibility]}
                  </div>
                </div>

                {/* Electricity */}
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Zap className="w-4 h-4 text-yellow-600" />
                    <span className="text-sm font-medium text-yellow-800">Electricity</span>
                  </div>
                  <p className="text-sm text-yellow-700">{data.electricity_label}</p>
                  <div className="mt-2 flex gap-1 flex-wrap">
                    {Array.from({ length: 24 }).map((_, h) => {
                      const edlHours = data.area_scores.electricity_hours ?? 12
                      const isEdl = h < edlHours
                      return (
                        <div
                          key={h}
                          title={isEdl ? `${h}:00 EDL` : `${h}:00 generator`}
                          className={`w-5 h-3 rounded-sm ${isEdl ? "bg-yellow-400" : "bg-gray-200"}`}
                        />
                      )
                    })}
                  </div>
                  <p className="text-xs text-yellow-600 mt-1">
                    Generator cost: ${data.area_scores.generator_cost ?? 40}/mo
                  </p>
                </div>

                {/* Commute */}
                {data.commute_minutes !== null && (
                  <div className="flex items-center gap-3 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
                    <Clock className="w-5 h-5 text-blue-600 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-blue-800">{data.commute_minutes} min commute</p>
                      <p className="text-xs text-blue-600">driving to your university</p>
                    </div>
                  </div>
                )}

                {/* Area scores */}
                <div className="space-y-2.5">
                  <ScoreBar value={data.area_scores.internet} max={5} label="Internet" />
                  <ScoreBar value={data.area_scores.transport} max={5} label="Transport" />
                  <ScoreBar value={data.area_scores.safety} max={5} label="Safety" />
                  <ScoreBar value={data.area_scores.student_vibe} max={5} label="Student vibe" />
                </div>
              </div>

              {/* Right: cost breakdown */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
                  <DollarSign className="w-4 h-4" /> True Monthly Cost
                </h3>
                <div className="space-y-2">
                  {[
                    { label: "Rent (your budget)", value: data.cost_breakdown.rent, icon: "🏠" },
                    { label: "Generator", value: data.cost_breakdown.generator, icon: "⚡" },
                    { label: "Water delivery", value: data.cost_breakdown.water, icon: "💧" },
                    { label: "Internet", value: data.cost_breakdown.internet, icon: "📡" },
                    { label: "Transport", value: data.cost_breakdown.transport, icon: "🚌" },
                  ].map(({ label, value, icon }) => (
                    <div key={label} className="flex justify-between items-center py-2 border-b last:border-b-0">
                      <span className="text-sm text-gray-600">{icon} {label}</span>
                      <span className="text-sm font-medium text-gray-800">${value}</span>
                    </div>
                  ))}
                  <div className="flex justify-between items-center pt-3 mt-1">
                    <span className="text-sm font-bold text-gray-900">Total / month</span>
                    <span className="text-lg font-bold text-primary">${data.cost_breakdown.total_monthly}</span>
                  </div>
                </div>

                {/* Composite scores */}
                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="bg-gray-50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-gray-800">
                      {Math.round(data.area_scores.livability_score * 100)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">Livability</div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-gray-800">
                      {Math.round(data.area_scores.student_score * 100)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">Student score</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {results.length > 0 && (
        <p className="text-xs text-gray-400 text-center mt-4">
          Run another simulation above to compare neighbourhoods side by side
        </p>
      )}
    </div>
  )
}
