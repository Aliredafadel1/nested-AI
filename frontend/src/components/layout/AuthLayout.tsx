import { Outlet } from "react-router-dom"

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="w-full max-w-md mx-auto">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-primary">NestAI</h1>
          <p className="text-gray-500 text-sm mt-1">Smart student housing in Lebanon</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border px-6 py-7">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
