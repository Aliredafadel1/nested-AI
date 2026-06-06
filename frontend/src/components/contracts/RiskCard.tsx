import type { RiskItem } from "../../api/contracts"

const styles = {
  high: "border-l-4 border-red-500 bg-red-50",
  medium: "border-l-4 border-yellow-500 bg-yellow-50",
  low: "border-l-4 border-green-500 bg-green-50",
}
const icons = { high: "⚠️", medium: "⚡", low: "ℹ️" }

export function RiskCard({ item }: { item: RiskItem }) {
  return (
    <div className={`rounded-lg p-4 ${styles[item.level]}`}>
      <div className="flex items-center gap-2 mb-2">
        <span>{icons[item.level]}</span>
        <span className="font-semibold text-sm capitalize">{item.level} Risk</span>
      </div>
      <blockquote className="text-xs text-gray-600 italic mb-2 border-l-2 border-gray-300 pl-2">
        "{item.clause_text}"
      </blockquote>
      <p className="text-sm text-gray-700">{item.explanation}</p>
    </div>
  )
}
