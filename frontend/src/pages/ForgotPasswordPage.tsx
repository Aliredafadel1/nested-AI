import { useState } from "react"
import { Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { forgotPassword } from "../api/users"
import toast from "react-hot-toast"

const schema = z.object({ email: z.string().email("Invalid email") })
type Form = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: Form) => {
    setLoading(true)
    try {
      await forgotPassword(data.email)
      setSent(true)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Request failed")
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <div className="text-center space-y-4 py-4">
        <div className="text-5xl">📬</div>
        <h2 className="text-lg font-semibold text-gray-800">Check your inbox</h2>
        <p className="text-sm text-gray-500 leading-relaxed">
          If that email is registered, we've sent a reset link.<br />
          The link expires in <strong>15 minutes</strong>.
        </p>
        <p className="text-sm text-gray-500">
          Didn't receive it?{" "}
          <button
            onClick={() => setSent(false)}
            className="text-primary hover:underline"
          >
            Try again
          </button>
        </p>
        <Link to="/login" className="block text-sm text-gray-400 hover:text-gray-600 mt-2">
          Back to sign in
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-gray-800">Forgot your password?</h2>
        <p className="text-sm text-gray-500 mt-1">
          Enter your email and we'll send you a reset link.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            {...register("email")}
            type="email"
            placeholder="you@example.com"
            className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-primary text-white rounded-lg font-medium disabled:opacity-60"
        >
          {loading ? "Sending…" : "Send reset link"}
        </button>
      </form>

      <p className="text-center text-sm text-gray-500">
        Remembered it?{" "}
        <Link to="/login" className="text-primary hover:underline">Sign in</Link>
      </p>
    </div>
  )
}
