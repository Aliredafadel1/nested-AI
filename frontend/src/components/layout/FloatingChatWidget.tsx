import { MessageCircle, X } from "lucide-react"
import { useChatStore } from "../../stores/chatStore"
import { ChatPanel } from "../agent/ChatPanel"

export function FloatingChatWidget() {
  const { isOpen, toggle, unreadCount } = useChatStore()

  return (
    <>
      {/* Floating bubble */}
      <button
        onClick={toggle}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary text-white shadow-lg flex items-center justify-center hover:bg-primary/90 transition"
        aria-label="Open AI Chat"
      >
        <MessageCircle className="w-6 h-6" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Panel — full-width on mobile, fixed 384px on sm+ */}
      {isOpen && (
        <div className="fixed bottom-0 right-0 left-0 sm:bottom-24 sm:right-6 sm:left-auto z-50 w-full sm:w-96 h-[85dvh] sm:h-[580px] bg-white sm:rounded-2xl shadow-2xl border flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-primary text-white">
            <span className="font-semibold text-sm">AI Housing Assistant</span>
            <button onClick={toggle}><X className="w-5 h-5" /></button>
          </div>
          <div className="flex-1 overflow-hidden">
            <ChatPanel />
          </div>
        </div>
      )}
    </>
  )
}
