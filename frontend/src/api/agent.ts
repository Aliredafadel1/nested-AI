import { useQuery, useMutation } from "@tanstack/react-query"
import { apiJson, apiFetch } from "./client"

export interface AreaScores {
  id: number; name: string; name_ar?: string | null
  electricity_hours: number; generator_cost: number
  internet: number; transport: number; safety: number; student_vibe: number
}

export async function streamChat(
  query: string,
  sessionId: string | null,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (e: Error) => void,
  onProgress?: (text: string) => void,
  language?: "ar" | "en",
) {
  try {
    const res = await apiFetch("/agent/chat", {
      method: "POST",
      body: JSON.stringify({ query, session_id: sessionId, language: language ?? null }),
    })
    if (!res.ok || !res.body) { onError(new Error(`HTTP ${res.status}`)); return }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ""
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split("\n")
      buf = lines.pop() ?? ""
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const payload = line.slice(6)
        if (payload === "[DONE]") { onDone(); return }
        // Detect progress events (JSON with type:"progress")
        try {
          const parsed = JSON.parse(payload)
          if (parsed?.type === "progress") {
            onProgress?.(parsed.text ?? "")
            continue
          }
        } catch { /* not JSON — treat as a plain token */ }
        onToken(payload)
      }
    }
    onDone()
  } catch (e) {
    onError(e as Error)
  }
}

export async function transcribeAudio(blob: Blob, filename = "audio.webm"): Promise<string> {
  const fd = new FormData(); fd.append("file", blob, filename)
  const data = await apiJson<{ text: string }>("/agent/transcribe", { method: "POST", body: fd })
  return data.text
}

export function useAreaScores(name: string) {
  return useQuery({
    queryKey: ["area", name],
    queryFn: () => apiJson<AreaScores>(`/areas/${encodeURIComponent(name)}`),
    enabled: !!name,
  })
}

export function useCompareAreas() {
  return useMutation({
    mutationFn: ({ area_a, area_b }: { area_a: string; area_b: string }) =>
      apiJson<{ area_a: AreaScores; area_b: AreaScores }>("/areas/compare", {
        method: "POST", body: JSON.stringify({ area_a, area_b }),
      }),
  })
}
