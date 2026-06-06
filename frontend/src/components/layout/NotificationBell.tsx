import { useState } from "react"
import { Bell } from "lucide-react"
import { useNotifStore } from "../../stores/notifStore"
import { useNotifications, useMarkRead } from "../../api/notifications"

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const { unreadCount, markRead: markLocal } = useNotifStore()
  const { data: notifs = [] } = useNotifications()
  const markRead = useMarkRead()

  const handleRead = (id: number) => {
    markRead.mutate(id)
    markLocal(id)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-full hover:bg-gray-100 transition"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5 text-gray-600" />
        {unreadCount > 0 && (
          <span className="absolute top-0.5 right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-10 w-80 bg-white border rounded-xl shadow-xl z-50 max-h-96 overflow-y-auto">
          <div className="px-4 py-3 border-b">
            <h4 className="font-semibold text-sm">Notifications</h4>
          </div>
          {notifs.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-gray-400">No notifications yet</div>
          ) : notifs.slice(0, 20).map((n) => (
            <div
              key={n.id}
              onClick={() => handleRead(n.id)}
              className={`px-4 py-3 cursor-pointer hover:bg-gray-50 border-b last:border-b-0
                ${n.read ? "opacity-60" : "bg-blue-50/50"}`}
            >
              <p className="text-sm text-gray-700">{n.type}</p>
              <p className="text-xs text-gray-400 mt-0.5">{new Date(n.created_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
