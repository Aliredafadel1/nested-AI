import { useRef, useEffect, useState } from "react"
import { Send, X } from "lucide-react"
import { useThread, useSendMessage } from "../../api/roommate"
import { useAuthStore } from "../../stores/authStore"

interface Props {
  requestId: number
  otherUserId: number
  onClose: () => void
}

export function MessageThread({ requestId, otherUserId, onClose }: Props) {
  const { user } = useAuthStore()
  const myId = user?.id
  const { data: messages = [] } = useThread(requestId)
  const send = useSendMessage(requestId)
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = () => {
    const text = input.trim()
    if (!text || send.isPending) return
    setInput("")
    send.mutate(text)
  }

  return (
    <div className="fixed inset-0 sm:inset-auto sm:bottom-6 sm:right-6 z-50 w-full sm:w-96 sm:h-[520px] h-full bg-white sm:rounded-2xl shadow-2xl border flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-primary text-white shrink-0">
        <div>
          <p className="font-semibold text-sm">Student #{otherUserId}</p>
          <p className="text-xs opacity-75">Roommate thread</p>
        </div>
        <button onClick={onClose} className="p-1 rounded hover:bg-white/20 transition">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {messages.length === 0 && (
          <p className="text-center text-sm text-gray-400 py-8">
            Say hello! Start the conversation.
          </p>
        )}
        {messages.map((msg) => {
          const isMe = msg.sender_id === myId
          return (
            <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-sm
                  ${isMe
                    ? "bg-primary text-white rounded-br-sm"
                    : "bg-gray-100 text-gray-800 rounded-bl-sm"}`}
              >
                <p>{msg.content}</p>
                <p className={`text-[10px] mt-0.5 ${isMe ? "text-white/60 text-right" : "text-gray-400"}`}>
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        className="border-t px-4 py-3 bg-white shrink-0 flex gap-2"
        style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      >
        <input
          className="flex-1 border rounded-xl px-3.5 py-2 text-base focus:outline-none focus:ring-2 focus:ring-primary/30"
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          onFocus={() => setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 350)}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || send.isPending}
          className="min-w-[44px] min-h-[44px] flex items-center justify-center bg-primary text-white rounded-xl disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
