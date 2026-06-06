import { Link, useNavigate } from "react-router-dom"
import { Home, MessageSquare, FileText, Users, LayoutDashboard, Menu, X } from "lucide-react"
import { useState } from "react"
import { useAuthStore } from "../../stores/authStore"
import { logout } from "../../api/users"
import { NotificationBell } from "./NotificationBell"

export function Navbar() {
  const { user, clear } = useAuthStore()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    clear()
    navigate("/login")
  }

  const isStudent = user?.role === "student"
  const isLandlord = user?.role === "landlord"

  const links = [
    { to: "/listings", label: "Listings", icon: Home, show: true },
    { to: "/agent", label: "AI Chat", icon: MessageSquare, show: isStudent },
    { to: "/contracts", label: "Contracts", icon: FileText, show: isStudent },
    { to: "/roommate", label: "Roommate", icon: Users, show: isStudent },
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, show: isLandlord },
  ].filter((l) => l.show)

  return (
    <nav className="sticky top-0 z-40 bg-white border-b shadow-sm">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/listings" className="font-bold text-lg text-primary">NestAI</Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-1">
          {links.map(({ to, label }) => (
            <Link key={to} to={to} className="px-3 py-2 text-sm rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition">
              {label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {user && <NotificationBell />}
          <div className="hidden md:flex items-center gap-2">
            {user && <span className="text-xs text-gray-500">{user.email}</span>}
            <button onClick={handleLogout} className="text-sm px-3 py-1.5 rounded-lg border hover:bg-gray-50 transition">
              Sign out
            </button>
          </div>
          <button className="md:hidden p-2" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t bg-white px-4 py-3 space-y-1">
          {links.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} onClick={() => setMobileOpen(false)}
              className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-gray-100">
              <Icon className="w-4 h-4" /> {label}
            </Link>
          ))}
          <button onClick={handleLogout} className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg">
            Sign out
          </button>
        </div>
      )}
    </nav>
  )
}
