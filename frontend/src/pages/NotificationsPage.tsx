import { useNotifications, useMarkRead } from "../api/notifications"
import { useNotifStore } from "../stores/notifStore"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"
import { EmptyState } from "../components/shared/EmptyState"

export function NotificationsPage() {
  const { data: notifs, isLoading } = useNotifications()
  const markRead = useMarkRead()
  const { markRead: markLocal } = useNotifStore()

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-xl font-bold mb-6">Notifications</h1>
      {!notifs || notifs.length === 0 ? (
        <EmptyState icon="🔔" title="No notifications yet" description="You'll see updates about your listings and matches here." />
      ) : (
        <div className="space-y-2">
          {notifs.map((n) => (
            <div
              key={n.id}
              onClick={() => { markRead.mutate(n.id); markLocal(n.id) }}
              className={`p-4 rounded-xl border cursor-pointer transition hover:bg-gray-50
                ${n.read ? "bg-white opacity-60" : "bg-blue-50/40 border-blue-100"}`}
            >
              <p className="text-sm font-medium text-gray-800">{n.type}</p>
              <p className="text-xs text-gray-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
