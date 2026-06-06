import { useState } from "react"
import { UserCheck } from "lucide-react"
import { DimensionScores } from "./DimensionScores"
import type { RoommateMatch } from "../../api/roommate"
import { useSendRoommateRequest } from "../../api/roommate"

export function MatchCard({ match }: { match: RoommateMatch }) {
  const [sent, setSent] = useState(false)
  const req = useSendRoommateRequest()

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold text-sm">
            {match.user_id}
          </div>
          <span className="text-sm text-gray-500">Student #{match.user_id}</span>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-primary">{Math.round(match.score * 100)}%</div>
          <div className="text-xs text-gray-400">match</div>
        </div>
      </div>
      <DimensionScores dimensions={match.dimensions} />
      <button
        onClick={() => { req.mutate(match.user_id); setSent(true) }}
        disabled={sent || req.isPending}
        className="w-full flex items-center justify-center gap-2 py-2 bg-primary text-white text-sm rounded-lg disabled:opacity-60"
      >
        <UserCheck className="w-4 h-4" />
        {sent ? "Request Sent ✓" : "Send Request"}
      </button>
    </div>
  )
}
