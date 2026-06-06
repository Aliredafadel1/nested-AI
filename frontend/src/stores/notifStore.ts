import { create } from "zustand"

export interface Notification {
  id: number
  type: string
  payload: Record<string, unknown>
  read: boolean
  created_at: string
}

interface NotifState {
  unreadCount: number
  notifications: Notification[]
  increment: () => void
  decrement: () => void
  setAll: (notifs: Notification[]) => void
  markRead: (id: number) => void
  addNew: (notif: Notification) => void
}

export const useNotifStore = create<NotifState>((set) => ({
  unreadCount: 0,
  notifications: [],
  increment: () => set((s) => ({ unreadCount: s.unreadCount + 1 })),
  decrement: () => set((s) => ({ unreadCount: Math.max(0, s.unreadCount - 1) })),
  setAll: (notifs) =>
    set({ notifications: notifs, unreadCount: notifs.filter((n) => !n.read).length }),
  markRead: (id) =>
    set((s) => ({
      notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
      unreadCount: Math.max(0, s.unreadCount - 1),
    })),
  addNew: (notif) =>
    set((s) => ({
      notifications: [notif, ...s.notifications],
      unreadCount: s.unreadCount + 1,
    })),
}))
