import { useState } from "react"
import { useAreaScores, useCompareAreas } from "../../api/agent"

function ScoreBar({ label, value, max }: { label: string; value: number; max: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{value}</span>
      </div>
      <div className="h-1.5 bg-gray-200 rounded-full">
        <div className="h-1.5 bg-primary rounded-full" style={{ width: `${(value / max) * 100}%` }} />
      </div>
    </div>
  )
}

export function AreaScoreSidebar() {
  const [area, setArea] = useState("Hamra")
  const [areaA, setAreaA] = useState("Hamra")
  const [areaB, setAreaB] = useState("Achrafieh")
  const [comparing, setComparing] = useState(false)
  const { data, isLoading } = useAreaScores(area)
  const compare = useCompareAreas()

  const AREAS = ["Hamra", "Gemmayzeh", "Achrafieh", "Mar Mikhael", "Verdun", "Badaro", "Ras Beirut", "Dekwaneh"]

  return (
    <div className="hidden lg:flex flex-col w-72 shrink-0 p-4 bg-gray-50 border-r overflow-y-auto">
      <h3 className="font-semibold text-sm mb-3">Area Intelligence</h3>
      <select
        className="text-sm border rounded-lg px-2 py-1.5 mb-4"
        value={area} onChange={(e) => setArea(e.target.value)}
      >
        {AREAS.map((a) => <option key={a}>{a}</option>)}
      </select>
      {isLoading ? <div className="text-xs text-gray-400">Loading…</div> : data && (
        <div className="space-y-2.5 mb-4">
          <ScoreBar label="Electricity (hrs/day)" value={data.electricity_hours} max={24} />
          <ScoreBar label="Generator Cost" value={data.generator_cost} max={80} />
          <ScoreBar label="Internet" value={data.internet} max={5} />
          <ScoreBar label="Transport" value={data.transport} max={5} />
          <ScoreBar label="Safety" value={data.safety} max={5} />
          <ScoreBar label="Student Vibe" value={data.student_vibe} max={5} />
        </div>
      )}
      <button
        onClick={() => setComparing(!comparing)}
        className="text-xs px-3 py-2 border border-primary/30 text-primary rounded-lg hover:bg-primary/5 mb-3"
      >
        {comparing ? "Hide Comparison" : "Compare 2 Areas"}
      </button>
      {comparing && (
        <div className="space-y-2">
          <select className="w-full text-sm border rounded-lg px-2 py-1.5"
            value={areaA} onChange={(e) => setAreaA(e.target.value)}>
            {AREAS.map((a) => <option key={a}>{a}</option>)}
          </select>
          <select className="w-full text-sm border rounded-lg px-2 py-1.5"
            value={areaB} onChange={(e) => setAreaB(e.target.value)}>
            {AREAS.map((a) => <option key={a}>{a}</option>)}
          </select>
          <button
            onClick={() => compare.mutate({ area_a: areaA, area_b: areaB })}
            className="w-full py-2 bg-primary text-white text-sm rounded-lg"
          >
            Compare
          </button>
          {compare.data && (
            <div className="text-xs mt-2 space-y-1">
              <p className="font-medium">{areaA} vs {areaB}</p>
              <p>EDL: {compare.data.area_a.electricity_hours}h vs {compare.data.area_b.electricity_hours}h</p>
              <p>Generator: ${compare.data.area_a.generator_cost} vs ${compare.data.area_b.generator_cost}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
