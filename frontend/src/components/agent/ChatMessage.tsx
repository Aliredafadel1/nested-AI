import { useState } from "react"
import { ThumbsUp, ThumbsDown } from "lucide-react"
import type { ChatMessage as Msg } from "../../stores/chatStore"
import { useChatStore } from "../../stores/chatStore"
import { apiJson } from "../../api/client"
import toast from "react-hot-toast"

interface Props { msg: Msg; turnIndex: number }

export function ChatMessage({ msg, turnIndex }: Props) {
  const isUser = msg.role === "user"
  const { sessionId } = useChatStore()
  const [rated, setRated] = useState<1 | -1 | null>(null)

  const submitFeedback = async (rating: 1 | -1) => {
    if (rated !== null || !sessionId || isUser || msg.isStreaming) return
    setRated(rating)
    try {
      await apiJson("/agent/feedback", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, turn_index: turnIndex, rating }),
      })
      toast.success(rating === 1 ? "Thanks for the feedback! 👍" : "Got it — we'll improve 👎", {
        duration: 2000,
      })
    } catch {
      setRated(null)
    }
  }

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} mb-3`}>
      <div
        className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? "bg-primary text-white rounded-br-sm"
            : "bg-gray-100 text-gray-800 rounded-bl-sm"
          }`}
      >
        {msg.content || (msg.isStreaming ? <span className="animate-pulse">▌</span> : "")}
        {msg.isStreaming && msg.content && <span className="animate-pulse ml-0.5">▌</span>}
      </div>

      {/* Feedback buttons — only on completed agent messages */}
      {!isUser && !msg.isStreaming && msg.content && (
        <div className="flex gap-1.5 mt-1 ml-1">
          <button
            onClick={() => submitFeedback(1)}
            className={`p-1 rounded transition ${
              rated === 1 ? "text-green-600" : "text-gray-300 hover:text-green-500"
            }`}
            title="Helpful"
          >
            <ThumbsUp className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => submitFeedback(-1)}
            className={`p-1 rounded transition ${
              rated === -1 ? "text-red-500" : "text-gray-300 hover:text-red-400"
            }`}
            title="Not helpful"
          >
            <ThumbsDown className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
