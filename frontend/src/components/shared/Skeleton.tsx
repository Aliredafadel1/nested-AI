function Block({ className }: { className: string }) {
  return <div className={`bg-gray-200 rounded animate-pulse ${className}`} />
}

export function SkeletonListingCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <div className="h-40 bg-gray-200 rounded-t-xl animate-pulse" />
      <div className="p-3 space-y-2">
        <div className="flex justify-between">
          <Block className="h-4 w-3/5" />
          <Block className="h-4 w-16" />
        </div>
        <Block className="h-3 w-2/5" />
        <Block className="h-5 w-20" />
      </div>
    </div>
  )
}

export function SkeletonMatchCard() {
  return (
    <div className="bg-white rounded-xl border p-4 space-y-3 animate-pulse">
      <div className="flex items-center gap-3">
        <Block className="h-10 w-10 rounded-full" />
        <div className="space-y-1.5 flex-1">
          <Block className="h-4 w-24" />
          <Block className="h-3 w-16" />
        </div>
        <Block className="h-8 w-16 rounded-lg" />
      </div>
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-2">
          <Block className="h-3 w-16 shrink-0" />
          <Block className="h-2 flex-1 rounded-full" />
          <Block className="h-3 w-8" />
        </div>
      ))}
    </div>
  )
}

export function SkeletonNotification() {
  return (
    <div className="p-4 rounded-xl border bg-white space-y-2 animate-pulse">
      <Block className="h-4 w-3/4" />
      <Block className="h-3 w-24" />
    </div>
  )
}

export function SkeletonListingDetail() {
  return (
    <div className="max-w-2xl mx-auto animate-pulse">
      <Block className="h-4 w-16 mb-4" />
      <div className="bg-white rounded-2xl border overflow-hidden">
        <Block className="h-64 rounded-none" />
        <div className="p-5 space-y-3">
          <div className="flex justify-between">
            <Block className="h-6 w-2/3" />
            <Block className="h-6 w-20" />
          </div>
          <Block className="h-4 w-1/3" />
          <Block className="h-5 w-24" />
          <Block className="h-4 w-full" />
          <Block className="h-4 w-4/5" />
          <Block className="h-4 w-3/5" />
          <div className="flex gap-3 mt-2">
            <Block className="h-10 w-24 rounded-xl" />
            <Block className="h-10 w-28 rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  )
}

export function SkeletonSavedCard() {
  return <SkeletonListingCard />
}
