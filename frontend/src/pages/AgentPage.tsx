import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { ChatPanel } from "../components/agent/ChatPanel"
import { AreaScoreSidebar } from "../components/agent/AreaScoreSidebar"

export function AgentPage() {
  const { user } = useAuthStore()
  if (user?.role !== "student") return <Navigate to="/listings" replace />

  return (
    <div className="flex h-[calc(100dvh-8rem)] -mx-4 -my-6 overflow-hidden">
      <AreaScoreSidebar />
      <div className="flex-1 flex flex-col bg-white min-w-0">
        <div className="px-4 py-3 border-b shrink-0">
          <h1 className="font-semibold text-gray-800">AI Housing Assistant</h1>
          <p className="text-xs text-gray-400">Ask about listings, generator hours, contracts, and more</p>
        </div>
        <div className="flex-1 overflow-hidden">
          <ChatPanel />
        </div>
      </div>
    </div>
  )
}
