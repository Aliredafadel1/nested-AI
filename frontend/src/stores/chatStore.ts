import { create } from "zustand"

export interface ChatMessage {
  id: string
  role: "user" | "agent"
  content: string
  isStreaming?: boolean
}

interface ChatState {
  isOpen: boolean
  messages: ChatMessage[]
  sessionId: string | null
  unreadCount: number
  toggle: () => void
  open: () => void
  addMessage: (msg: ChatMessage) => void
  updateLastAgentMessage: (chunk: string) => void
  finalizeLastMessage: () => void
  setSessionId: (id: string) => void
  clearUnread: () => void
  incrementUnread: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  isOpen: false,
  messages: [],
  sessionId: null,
  unreadCount: 0,
  toggle: () => set((s) => ({ isOpen: !s.isOpen, unreadCount: s.isOpen ? s.unreadCount : 0 })),
  open: () => set({ isOpen: true, unreadCount: 0 }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAgentMessage: (chunk) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === "agent") {
        msgs[msgs.length - 1] = { ...last, content: last.content + chunk }
      }
      return { messages: msgs }
    }),
  finalizeLastMessage: () =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last) msgs[msgs.length - 1] = { ...last, isStreaming: false }
      return { messages: msgs, unreadCount: s.isOpen ? 0 : s.unreadCount + 1 }
    }),
  setSessionId: (id) => set({ sessionId: id }),
  clearUnread: () => set({ unreadCount: 0 }),
  incrementUnread: () => set((s) => ({ unreadCount: s.unreadCount + 1 })),
}))
