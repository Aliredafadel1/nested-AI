import { useNotifications, useMarkRead } from "../api/notifications"
import { useNotifStore } from "../stores/notifStore"
import { SkeletonNotification } from "../components/shared/Skeleton"
import { EmptyState } from "../components/shared/EmptyState"

const TYPE_LABELS: Record<string, string> = {
  roommate_request_sent: "Roommate request sent",
  roommate_request_received: "New roommate request",
  listing_saved: "Someone saved your listing",
  contract_analyzed: "Contract analysis ready",
  fraud_flagged: "Listing flagged for review",
}

export function NotificationsPage() {
  const { data: notifs, isLoading, isError, refetch } = useNotifications()
  const markRead = useMarkRead()
  const { markRead: markLocal } = useNotifStore()

  if (isLoading) {
    return (
      <div className="max-w-xl mx-auto">
        <div className="h-7 w-36 bg-gray-200 rounded animate-pulse mb-6" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonNotification key={i} />)}
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-xl mx-auto">
        <h1 className="text-xl font-bold mb-6">Notifications</h1>
        <EmptyState
          icon="⚠️"
          title="Could not load notifications"
          description="Check your connection and try again."
          action={<button onClick={() => refetch()} className="px-4 py-2 bg-primary text-white rounded-lg text-sm">Retry</button>}
        />
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-xl font-bold mb-6">Notifications</h1>
      {!notifs || notifs.length === 0 ? (
        <EmptyState
          icon="🔔"
          title="No notifications yet"
          description="You'll see updates about your listings, matches, and contracts here."
        />
      ) : (
        <div className="space-y-2">
          {notifs.map((n) => (
            <div
              key={n.id}
              onClick={() => { markRead.mutate(n.id); markLocal(n.id) }}
              className={`p-4 rounded-xl border cursor-pointer transition hover:bg-gray-50
                ${n.read ? "bg-white opacity-60" : "bg-blue-50/40 border-blue-100"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-gray-800">
                  {TYPE_LABELS[n.type] ?? n.type}
                </p>
                {!n.read && <span className="shrink-0 w-2 h-2 rounded-full bg-primary mt-1.5" />}
              </div>
              <p className="text-xs text-gray-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
