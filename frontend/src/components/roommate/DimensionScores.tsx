interface Props {
  dimensions: { sleep: number; study: number; cleanliness: number; guests: number; budget: number }
}
const LABELS: [keyof Props["dimensions"], string][] = [
  ["sleep", "Sleep Schedule"], ["study", "Study Habits"], ["cleanliness", "Cleanliness"],
  ["guests", "Guests Policy"], ["budget", "Budget Match"],
]

export function DimensionScores({ dimensions }: Props) {
  return (
    <div className="space-y-2">
      {LABELS.map(([key, label]) => (
        <div key={key}>
          <div className="flex justify-between text-xs mb-0.5">
            <span className="text-gray-600">{label}</span>
            <span className="font-medium">{Math.round(dimensions[key] * 100)}%</span>
          </div>
          <div className="h-1.5 bg-gray-200 rounded-full">
            <div
              className="h-1.5 bg-primary rounded-full transition-all"
              style={{ width: `${dimensions[key] * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
