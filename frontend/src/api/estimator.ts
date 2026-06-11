import { useMutation, useQuery } from "@tanstack/react-query"
import { apiJson } from "./client"

export interface EstimateOut {
  rent: number; generator: number; water: number; internet: number
  transport: number; total_monthly: number; commute_minutes: number | null
}

export function useCommute(rent: number, neighbourhood_id: number, university_id: number | null | undefined) {
  return useQuery({
    queryKey: ["commute", neighbourhood_id, university_id],
    queryFn: () => apiJson<EstimateOut>("/estimator/calculate", {
      method: "POST",
      body: JSON.stringify({ rent, neighbourhood_id, university_id }),
    }),
    enabled: !!university_id && !!neighbourhood_id,
    staleTime: 30 * 60_000,
  })
}

export function useCalculateCost() {
  return useMutation({
    mutationFn: (data: { rent: number; neighbourhood_id: number; university_id?: number | null }) =>
      apiJson<EstimateOut>("/estimator/calculate", { method: "POST", body: JSON.stringify(data) }),
  })
}

// ── Relocation Simulator ──────────────────────────────────────────────────────

export interface AreaScores {
  electricity_hours: number | null; electricity_reliability: number
  generator_cost: number | null; internet: number | null; transport: number | null
  safety: number | null; student_vibe: number | null
  livability_score: number; student_score: number
}

export interface CostBreakdown {
  rent: number; generator: number; water: number; internet: number; transport: number; total_monthly: number
}

export interface SimulateOut {
  neighbourhood_name: string; neighbourhood_name_ar: string | null
  area_scores: AreaScores; cost_breakdown: CostBreakdown
  commute_minutes: number | null; fit_score: number
  electricity_label: string; budget_feasibility: "comfortable" | "tight" | "over budget"
}

export function useSimulate() {
  return useMutation({
    mutationFn: (data: { neighbourhood_id: number; budget: number; university_id?: number | null }) =>
      apiJson<SimulateOut>("/estimator/simulate", { method: "POST", body: JSON.stringify(data) }),
  })
}
