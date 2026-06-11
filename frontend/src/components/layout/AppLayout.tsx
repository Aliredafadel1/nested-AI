import { Outlet, Navigate } from "react-router-dom"
import { useEffect } from "react"
import { Navbar } from "./Navbar"
import { FloatingChatWidget } from "./FloatingChatWidget"
import { useAuthStore } from "../../stores/authStore"
import { useNotifStore } from "../../stores/notifStore"
import { connectSSE, useNotifications } from "../../api/notifications"
import toast from "react-hot-toast"

export function AppLayout() {
  const { accessToken } = useAuthStore()
  const { addNew, increment, setAll } = useNotifStore()
  const { data: initialNotifs } = useNotifications()

  // Sync unread count from API on mount so badge survives page refresh
  useEffect(() => {
    if (initialNotifs) setAll(initialNotifs)
  }, [initialNotifs, setAll])

  useEffect(() => {
    if (!accessToken) return
    const disconnect = connectSSE((notif) => {
      addNew({ ...notif, read: false })
      increment()
      toast(`📬 ${notif.type}`, { duration: 4000 })
    })
    return disconnect
  }, [accessToken, addNew, increment])

  if (!accessToken) return <Navigate to="/login" replace />

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>
      <FloatingChatWidget />
    </div>
  )
}
