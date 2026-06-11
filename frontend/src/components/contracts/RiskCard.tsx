import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import type { RiskItem } from "../../api/contracts"

const styles = {
  high: "border-l-4 border-red-500 bg-red-50",
  medium: "border-l-4 border-yellow-500 bg-yellow-50",
  low: "border-l-4 border-green-500 bg-green-50",
}
const icons = { high: "⚠️", medium: "⚡", low: "ℹ️" }

export function RiskCard({ item }: { item: RiskItem }) {
  const [open, setOpen] = useState(item.level === "high")

  return (
    <div className={`rounded-lg overflow-hidden ${styles[item.level]}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-2 p-4 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span>{icons[item.level]}</span>
          <span className="font-semibold text-sm capitalize">{item.level} Risk</span>
          {!open && (
            <span className="text-xs text-gray-500 truncate hidden sm:block ml-1">
              — {item.explanation.slice(0, 60)}{item.explanation.length > 60 ? "…" : ""}
            </span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-500 shrink-0" /> : <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4">
          <blockquote className="text-xs text-gray-600 italic mb-2 border-l-2 border-gray-300 pl-2">
            "{item.clause_text}"
          </blockquote>
          <p className="text-sm text-gray-700">{item.explanation}</p>
        </div>
      )}
    </div>
  )
}
