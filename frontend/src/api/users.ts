import { useQuery } from "@tanstack/react-query"
import { apiJson } from "./client"

export interface TokenResponse { access_token: string; token_type: string; role: string }
export interface UserMe {
  id: number; email: string; role: string
  profile?: { university_id?: number | null; budget_min?: number | null; budget_max?: number | null;
    sleep_schedule?: string | null; study_habits?: string | null; cleanliness?: string | null;
    guests?: string | null; language?: string | null; priorities?: string[] } | null
}

export const register = (data: { email: string; password: string; role: string }) =>
  apiJson<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify(data) })

export const login = (data: { email: string; password: string }) =>
  apiJson<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(data) })

export const logout = () =>
  apiJson("/auth/logout", { method: "POST" }).catch(() => {})

export const refresh = () =>
  apiJson<TokenResponse>("/auth/refresh", { method: "POST" })

export const getMe = () => apiJson<UserMe>("/users/me")

export function useMe() {
  return useQuery({ queryKey: ["me"], queryFn: () => apiJson<UserMe>("/users/me"), staleTime: 5 * 60_000 })
}

export const onboard = (data: Record<string, unknown>) =>
  apiJson("/users/onboarding", { method: "POST", body: JSON.stringify(data) })

export const forgotPassword = (email: string) =>
  apiJson<{ message: string }>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  })

export const resetPassword = (token: string, new_password: string) =>
  apiJson("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, new_password }) })
