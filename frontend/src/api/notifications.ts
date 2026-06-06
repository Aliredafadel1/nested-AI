import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiJson, BASE } from "./client"
import { useAuthStore } from "../stores/authStore"

export interface Notification {
  id: number; type: string; payload: Record<string, unknown>; read: boolean; created_at: string
}

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiJson<Notification[]>("/notifications"),
  })
}

export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      apiJson(`/notifications/${id}/read`, { method: "POST" }).catch(() => {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  })
}

export function connectSSE(onMessage: (n: Notification) => void): () => void {
  const token = useAuthStore.getState().accessToken
  const url = `${BASE}/notifications/stream`
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}

  let active = true
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(url, { headers, signal: controller.signal, credentials: "include" })
      if (!res.body) return
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ""
      while (active) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split("\n")
        buf = lines.pop() ?? ""
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          try { onMessage(JSON.parse(line.slice(6))) } catch { /* ignore parse errors */ }
        }
      }
    } catch { /* SSE disconnect */ }
  })()

  return () => { active = false; controller.abort() }
}
