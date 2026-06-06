import { useAuthStore } from "../stores/authStore"

// Relative URL in dev — Vite proxy routes to http://localhost:8000
// Set VITE_API_URL for production deployments
const BASE = import.meta.env.VITE_API_URL || ""

async function refreshToken(): Promise<string | null> {
  try {
    const res = await fetch(`${BASE}/auth/refresh`, { method: "POST", credentials: "include" })
    if (!res.ok) return null
    const data = await res.json()
    useAuthStore.getState().setToken(data.access_token)
    return data.access_token
  } catch {
    return null
  }
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = useAuthStore.getState().accessToken
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (init.body instanceof FormData) delete headers["Content-Type"]

  let res = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "include" })

  if (res.status === 401) {
    const newToken = await refreshToken()
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`
      res = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "include" })
    }
    if (res.status === 401) {
      useAuthStore.getState().clear()
      window.location.href = "/login"
    }
  }

  return res
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, init)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export { BASE }
