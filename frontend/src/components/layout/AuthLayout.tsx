import { Outlet } from "react-router-dom"

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary">NestAI</h1>
          <p className="text-gray-500 text-sm mt-1">Smart student housing in Lebanon</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border p-8">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
