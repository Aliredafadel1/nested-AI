import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { register as apiRegister, getMe } from "../api/users"
import { useAuthStore } from "../stores/authStore"
import toast from "react-hot-toast"

const schema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(8, "At least 8 characters"),
  role: z.enum(["student", "landlord"]),
})
type Form = z.infer<typeof schema>

export function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema), defaultValues: { role: "student" },
  })

  const onSubmit = async (data: Form) => {
    setLoading(true)
    try {
      const tok = await apiRegister(data)
      setAuth(tok.access_token, { id: 0, email: data.email, role: tok.role })
      const me = await getMe()
      setAuth(tok.access_token, { id: me.id, email: me.email, role: me.role })
      if (tok.role === "landlord") { navigate("/dashboard"); return }
      navigate("/onboarding")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Registration failed")
    } finally { setLoading(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <h2 className="text-xl font-bold text-gray-800 mb-2">Create account</h2>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
        <select {...register("role")} className="w-full border rounded-lg px-3 py-2.5 text-sm">
          <option value="student">Student</option>
          <option value="landlord">Landlord</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input {...register("email")} type="email" className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
        {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
        <input {...register("password")} type="password" className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
        {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
      </div>
      <button type="submit" disabled={loading} className="w-full py-2.5 bg-primary text-white rounded-lg font-medium disabled:opacity-60">
        {loading ? "Creating…" : "Create account"}
      </button>
      <p className="text-center text-sm text-gray-500">
        Already have an account? <Link to="/login" className="text-primary hover:underline">Sign in</Link>
      </p>
    </form>
  )
}
