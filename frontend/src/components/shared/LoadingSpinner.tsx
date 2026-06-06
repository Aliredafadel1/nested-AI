export function LoadingSpinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const s = size === "sm" ? "h-4 w-4" : size === "lg" ? "h-12 w-12" : "h-8 w-8"
  return (
    <div className="flex items-center justify-center py-8">
      <div className={`${s} border-4 border-primary border-t-transparent rounded-full animate-spin`} />
    </div>
  )
}
