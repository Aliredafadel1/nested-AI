import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiJson } from "./client"

export interface RoommateMatch {
  user_id: number; score: number
  dimensions: { sleep: number; study: number; cleanliness: number; guests: number; budget: number }
}

export interface RoommateRequest {
  id: number; from_user_id: number; to_user_id: number
  score: number | null; dimensions: Record<string, number>
  status: "pending" | "accepted" | "declined"; created_at: string
}

export interface RoommateMessage {
  id: number; request_id: number; sender_id: number
  content: string; created_at: string
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roommate-requests"] }),
  })
}

export function useMyRequests() {
  return useQuery({
    queryKey: ["roommate-requests"],
    queryFn: () => apiJson<RoommateRequest[]>("/roommate/requests"),
  })
}

export function useRespondToRequest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ requestId, accept }: { requestId: number; accept: boolean }) =>
      apiJson<RoommateRequest>(`/roommate/requests/${requestId}`, {
        method: "PATCH",
        body: JSON.stringify({ accept }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roommate-requests"] }),
  })
}

export function useThread(requestId: number | null) {
  return useQuery({
    queryKey: ["roommate-thread", requestId],
    queryFn: () => apiJson<RoommateMessage[]>(`/roommate/requests/${requestId}/messages`),
    enabled: !!requestId,
    refetchInterval: 5000,
  })
}

export function useSendMessage(requestId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (content: string) =>
      apiJson<RoommateMessage>(`/roommate/requests/${requestId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roommate-thread", requestId] }),
  })
}
