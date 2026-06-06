import { useMutation } from "@tanstack/react-query"
import { apiJson } from "./client"

export interface EstimateOut {
  rent: number; generator: number; water: number; internet: number
  transport: number; total_monthly: number; commute_minutes: number | null
}

export function useCalculateCost() {
  return useMutation({
    mutationFn: (data: { rent: number; neighbourhood_id: number; university_id?: number | null }) =>
      apiJson<EstimateOut>("/estimator/calculate", { method: "POST", body: JSON.stringify(data) }),
  })
}
