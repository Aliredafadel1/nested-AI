import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiJson } from "./client"

export interface RoommateMatch {
  user_id: number; score: number
  dimensions: { sleep: number; study: number; cleanliness: number; guests: number; budget: number }
}

export function useRoommateMatches() {
  return useQuery({
    queryKey: ["roommate-matches"],
    queryFn: () => apiJson<RoommateMatch[]>("/roommate/matches"),
    retry: (count, err) => !(err instanceof Error && err.message.includes("422")) && count < 2,
  })
}

export function useSendRoommateRequest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (to_user_id: number) =>
      apiJson("/roommate/requests", { method: "POST", body: JSON.stringify({ to_user_id }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roommate-matches"] }),
  })
}
