import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { login, getMe } from "../api/users"
import { apiJson } from "../api/client"
import { useAuthStore } from "../stores/authStore"
import toast from "react-hot-toast"

const schema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(1, "Required"),
})
type Form = z.infer<typeof schema>

export function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: Form) => {
    setLoading(true)
    try {
      const tok = await login(data)
      setAuth(tok.access_token, { id: 0, email: data.email, role: tok.role })
      const me = await getMe()
      setAuth(tok.access_token, { id: me.id, email: me.email, role: me.role })
      if (tok.role === "landlord") { navigate("/dashboard"); return }
      if (me.profile?.university_id) { navigate("/listings"); return }
      navigate("/onboarding")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Login failed")
    } finally { setLoading(false) }
  }

  const onDemo = async () => {
    setDemoLoading(true)
    try {
      const tok = await apiJson<{ access_token: string; role: string }>("/auth/demo", { method: "POST" })
      setAuth(tok.access_token, { id: 0, email: "jawad@demo.com", role: tok.role })
      const me = await getMe()
      setAuth(tok.access_token, { id: me.id, email: me.email, role: me.role })
      toast.success("Welcome, Jawad! 👋")
      navigate("/listings")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Demo login failed")
    } finally { setDemoLoading(false) }
  }

  return (
    <div className="space-y-4">
      {/* Demo banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
        <p className="text-xs text-amber-700 font-medium mb-2">
          🎓 Try the full platform instantly — no account needed
        </p>
        <button
          onClick={onDemo}
          disabled={demoLoading}
          className="w-full py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-semibold text-sm transition disabled:opacity-60"
        >
          {demoLoading ? "Loading demo…" : "✨ Try Demo as Jawad (Student)"}
        </button>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 border-t border-gray-200" />
        <span className="text-xs text-gray-400">or sign in</span>
        <div className="flex-1 border-t border-gray-200" />
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input {...register("email")} type="email" className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
          {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="text-sm font-medium text-gray-700">Password</label>
            <Link to="/forgot-password" className="text-xs text-primary hover:underline">Forgot password?</Link>
          </div>
          <input {...register("password")} type="password" className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
          {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
        </div>
        <button type="submit" disabled={loading} className="w-full py-2.5 bg-primary text-white rounded-lg font-medium disabled:opacity-60">
          {loading ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-center text-sm text-gray-500">
          No account? <Link to="/register" className="text-primary hover:underline">Register</Link>
        </p>
      </form>
    </div>
  )
}
