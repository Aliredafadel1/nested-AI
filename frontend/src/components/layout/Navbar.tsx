import { Link, useNavigate, useLocation } from "react-router-dom"
import { Home, MessageSquare, FileText, Users, LayoutDashboard, Menu, X,
         UserCircle, Heart, BarChart2, MapPin, ChevronDown } from "lucide-react"
import { useState, useRef, useEffect } from "react"
import { useAuthStore } from "../../stores/authStore"
import { logout } from "../../api/users"
import { NotificationBell } from "./NotificationBell"

export function Navbar() {
  const { user, clear } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const moreRef = useRef<HTMLDivElement>(null)

  const handleLogout = async () => {
    await logout(); clear(); navigate("/login")
  }

  // Close "More" dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  const isStudent = user?.role === "student"
  const isLandlord = user?.role === "landlord"

  const primary = [
    { to: "/listings",  label: "Listings",  icon: Home,         show: true },
    { to: "/agent",     label: "AI Chat",   icon: MessageSquare, show: isStudent },
    { to: "/compare",   label: "Compare",   icon: BarChart2,    show: isStudent },
    { to: "/roommate",  label: "Roommate",  icon: Users,         show: isStudent },
    { to: "/contracts", label: "Contracts", icon: FileText,      show: isStudent },
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, show: isLandlord },
  ].filter((l) => l.show)

  const secondary = [
    { to: "/simulator", label: "Relocation Simulator", icon: MapPin,   show: isStudent },
    { to: "/saved",     label: "Saved Listings",     icon: Heart,      show: isStudent },
    { to: "/onboarding",label: "My Profile",         icon: UserCircle, show: isStudent },
  ].filter((l) => l.show)

  const allLinks = [...primary, ...secondary]
  const isSecondaryActive = secondary.some((l) => location.pathname.startsWith(l.to))

  const navLink = "px-3 py-2 text-sm rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition"
  const activeNavLink = "px-3 py-2 text-sm rounded-lg bg-primary/10 text-primary font-medium"

  return (
    <nav className="sticky top-0 z-40 bg-white border-b shadow-sm">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/listings" className="font-bold text-lg text-primary shrink-0">NestAI</Link>

        {/* Desktop primary links */}
        <div className="hidden md:flex items-center gap-0.5">
          {primary.map(({ to, label }) => (
            <Link key={to} to={to}
              className={location.pathname.startsWith(to) && to !== "/" ? activeNavLink : navLink}>
              {label}
            </Link>
          ))}

          {/* "More" dropdown for secondary links */}
          {secondary.length > 0 && (
            <div ref={moreRef} className="relative">
              <button
                onClick={() => setMoreOpen(!moreOpen)}
                className={`flex items-center gap-1 ${isSecondaryActive ? activeNavLink : navLink}`}
              >
                More <ChevronDown className={`w-3.5 h-3.5 transition-transform ${moreOpen ? "rotate-180" : ""}`} />
              </button>
              {moreOpen && (
                <div className="absolute top-10 left-0 w-52 bg-white border rounded-xl shadow-lg py-1 z-50">
                  {secondary.map(({ to, label, icon: Icon }) => (
                    <Link key={to} to={to}
                      onClick={() => setMoreOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition">
                      <Icon className="w-4 h-4 text-gray-400" /> {label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {user && <NotificationBell />}
          <div className="hidden md:flex items-center gap-2">
            <button onClick={handleLogout} className="text-sm px-3 py-1.5 rounded-lg border hover:bg-gray-50 transition">
              Sign out
            </button>
          </div>
          <button className="md:hidden p-2" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu — all links */}
      {mobileOpen && (
        <div className="md:hidden border-t bg-white px-4 py-3 space-y-1">
          {allLinks.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} onClick={() => setMobileOpen(false)}
              className="flex items-center gap-2 px-3 py-2.5 text-sm rounded-lg hover:bg-gray-100">
              <Icon className="w-4 h-4 text-gray-400" /> {label}
            </Link>
          ))}
          <button onClick={handleLogout}
            className="w-full text-left px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 rounded-lg">
            Sign out
          </button>
        </div>
      )}
    </nav>
  )
}
