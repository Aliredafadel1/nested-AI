import { create } from "zustand"

interface User {
  id: number
  email: string
  role: string
}

interface AuthState {
  accessToken: string | null
  user: User | null
  setAuth: (token: string, user: User) => void
  setToken: (token: string) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  setAuth: (accessToken, user) => set({ accessToken, user }),
  setToken: (accessToken) => set({ accessToken }),
  clear: () => set({ accessToken: null, user: null }),
}))
