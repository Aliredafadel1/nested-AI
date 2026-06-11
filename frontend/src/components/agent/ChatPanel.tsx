import { useState, useRef, useEffect } from "react"
import { Send } from "lucide-react"
import { v4 as uuid } from "uuid"
import { ChatMessage } from "./ChatMessage"
import { VoiceButton } from "./VoiceButton"
import { QuickChips } from "./QuickChips"
import { streamChat } from "../../api/agent"
import { useChatStore } from "../../stores/chatStore"
import toast from "react-hot-toast"

export function ChatPanel() {
  const { messages, sessionId, addMessage, updateLastAgentMessage, finalizeLastMessage, setSessionId } = useChatStore()
  const [input, setInput] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [lang, setLang] = useState<"en" | "ar" | undefined>(undefined)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages, progress])

  const send = async (text: string) => {
    if (!text.trim() || streaming) return
    const userMsg = { id: uuid(), role: "user" as const, content: text }
    addMessage(userMsg)
    const agentMsg = { id: uuid(), role: "agent" as const, content: "", isStreaming: true }
    addMessage(agentMsg)
    setInput("")
    setStreaming(true)
    setProgress("🧠 Understanding your query…")

    let sid = sessionId
    if (!sid) { sid = uuid(); setSessionId(sid) }

    let retried = false
    const tryStream = () =>
      streamChat(
        text, sid!,
        (token) => { setProgress(null); updateLastAgentMessage(token) },
        () => { setProgress(null); finalizeLastMessage(); setStreaming(false) },
        async () => {
          if (!retried) {
            retried = true
            toast("Connection lost — retrying…")
            await new Promise((r) => setTimeout(r, 2000))
            tryStream()
          } else {
            setProgress(null)
            updateLastAgentMessage("Sorry, I couldn't reach the server. Please try again.")
            finalizeLastMessage()
            setStreaming(false)
          }
        },
        (text) => setProgress(text),
        lang,
      )
    tryStream()
  }

  return (
    <div className="flex flex-col h-full min-h-[400px]">
      {/* Language toggle */}
      <div className="flex justify-end px-4 pt-3 pb-1">
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs font-medium">
          <button
            onClick={() => setLang(undefined)}
            className={`px-3 py-1.5 transition ${lang === undefined ? "bg-primary text-white" : "bg-white text-gray-500 hover:bg-gray-50"}`}
          >
            Auto
          </button>
          <button
            onClick={() => setLang("en")}
            className={`px-3 py-1.5 transition ${lang === "en" ? "bg-primary text-white" : "bg-white text-gray-500 hover:bg-gray-50"}`}
          >
            EN
          </button>
          <button
            onClick={() => setLang("ar")}
            className={`px-3 py-1.5 transition ${lang === "ar" ? "bg-primary text-white" : "bg-white text-gray-500 hover:bg-gray-50"}`}
          >
            عربي
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm py-12">
            {"Ask me anything about housing in Lebanon 🏠"}
          </div>
        )}
        {messages.map((msg, idx) => (
          <ChatMessage key={msg.id} msg={msg} turnIndex={Math.floor(idx / 2)} />
        ))}
        {progress && (
          <div className="flex items-center gap-2 text-xs text-gray-400 py-2 pl-1">
            <span className="flex gap-0.5">
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:300ms]" />
            </span>
            {progress}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div
        className="border-t px-4 py-3 bg-white shrink-0"
        style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      >
        <QuickChips onSelect={(t) => send(t)} />
        <div className="flex gap-2 mt-2">
          <input
            className={`flex-1 border rounded-xl px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-primary/30 ${lang === "ar" ? "text-right" : ""}`}
            placeholder={lang === "ar" ? "اسأل عن الشقق، الأحياء، ساعات الكهرباء…" : "Ask about listings, areas, generator hours… (or type in 3arabizi / عربي)"}
            dir={lang === "ar" ? "rtl" : "ltr"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
            onFocus={() => setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 350)}
            disabled={streaming}
          />
          <VoiceButton onTranscript={(t) => { setInput(t); send(t) }} />
          <button
            onClick={() => send(input)}
            disabled={streaming || !input.trim()}
            className="min-w-[44px] min-h-[44px] flex items-center justify-center bg-primary text-white rounded-xl disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
