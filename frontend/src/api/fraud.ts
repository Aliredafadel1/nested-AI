import { useQuery } from "@tanstack/react-query"
import { apiJson } from "./client"

export interface FraudReport {
  listing_id: number; score: number; price_zscore: number | null
  evidence: { price_flags: string[]; phone_flags: string[]; photo_flags: string[]; text_flags: string[] }
  computed_at: string
}

export function useFraudReport(listingId: number) {
  return useQuery({
    queryKey: ["fraud", listingId],
    queryFn: () => apiJson<FraudReport>(`/fraud/${listingId}`),
    staleTime: 12 * 60 * 60 * 1000,
  })
}
