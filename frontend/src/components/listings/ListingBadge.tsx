interface Props { fraud_score?: number | null; phone_verified?: boolean }

export function ListingBadge({ fraud_score, phone_verified }: Props) {
  return (
    <div className="flex gap-1 flex-wrap">
      {phone_verified && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
          ✓ Verified
        </span>
      )}
      {fraud_score != null && fraud_score >= 0.7 && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
          ⚠ High Risk
        </span>
      )}
      {fraud_score != null && fraud_score >= 0.4 && fraud_score < 0.7 && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 font-medium">
          ⚡ Moderate
        </span>
      )}
    </div>
  )
}
