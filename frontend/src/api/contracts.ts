import { useQuery, useMutation } from "@tanstack/react-query"
import { apiJson } from "./client"

export interface RiskItem { level: "high" | "medium" | "low"; clause_text: string; explanation: string }
export interface Contract {
  id: number; ocr_used: boolean
  status: "pending" | "ocr_running" | "analyzing" | "complete" | "failed"
  analysis: { risk_items: RiskItem[] } | null; created_at: string
}

export function useUploadContract() {
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData(); fd.append("file", file)
      return apiJson<{ contract_id: number; status: string }>("/contracts/analyze", { method: "POST", body: fd })
    },
  })
}

export function useContract(id: number | null) {
  return useQuery({
    queryKey: ["contract", id],
    queryFn: () => apiJson<Contract>(`/contracts/${id}`),
    enabled: id !== null,
    refetchInterval: (query: any) =>
      ["complete", "failed"].includes(query?.state?.data?.status) ? false : 3000,
  })
}
