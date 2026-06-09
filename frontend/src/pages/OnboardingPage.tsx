import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { onboard, getMe } from "../api/users"
import { useAuthStore } from "../stores/authStore"
import toast from "react-hot-toast"

const UNIS = [
  { id: 1, name: "American University of Beirut (AUB)" },
  { id: 2, name: "Lebanese American University (LAU)" },
  { id: 3, name: "Lebanese University (LU)" },
  { id: 4, name: "Saint Joseph University (USJ)" },
  { id: 5, name: "Notre Dame University (NDU)" },
  { id: 6, name: "Haigazian University" },
  { id: 7, name: "Holy Spirit University of Kaslik (USEK)" },
  { id: 8, name: "University of Balamand" },
  { id: 9, name: "Rafik Hariri University (RHU)" },
  { id: 10, name: "Lebanese International University (LIU)" },
]

const STEPS = ["University", "Budget", "Sleep", "Study", "Cleanliness", "Guests", "Language", "Priorities"]

export function OnboardingPage() {
  const navigate = useNavigate()
  useAuthStore()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<Record<string, any>>({
    university_id: UNIS[0].id, budget_min: 300, budget_max: 700,
    sleep_schedule: "flexible", study_habits: "moderate", cleanliness: "medium",
    guests: "sometimes", language: "english", priorities: [],
  })

  useEffect(() => {
    getMe().then((me) => {
      if (me.profile) {
        setData((d) => ({
          ...d,
          university_id:  me.profile.university_id ?? d.university_id,
          budget_min:     me.profile.budget_min     ?? d.budget_min,
          budget_max:     me.profile.budget_max     ?? d.budget_max,
          sleep_schedule: me.profile.sleep_schedule ?? d.sleep_schedule,
          study_habits:   me.profile.study_habits   ?? d.study_habits,
          cleanliness:    me.profile.cleanliness    ?? d.cleanliness,
          guests:         me.profile.guests         ?? d.guests,
          language:       me.profile.language       ?? d.language,
          priorities:     me.profile.priorities     ?? d.priorities,
        }))
      }
    }).catch(() => {})
  }, [])

  const set = (k: string, v: any) => setData((d) => ({ ...d, [k]: v }))

  const submit = async () => {
    setLoading(true)
    try {
      await onboard(data)
      navigate("/listings")
    } catch (e: any) { toast.error(e.message || "Failed to save profile") }
    finally { setLoading(false) }
  }

  const pct = ((step + 1) / STEPS.length) * 100

  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{STEPS[step]}</span><span>{step + 1} / {STEPS.length}</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full"><div className="h-2 bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} /></div>
      </div>

      {step === 0 && (
        <div>
          <label className="block text-sm font-medium mb-2">Your university</label>
          <select className="w-full border rounded-lg px-3 py-2.5 text-sm"
            value={data.university_id} onChange={(e) => set("university_id", Number(e.target.value))}>
            {UNIS.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
        </div>
      )}
      {step === 1 && (
        <div className="space-y-3">
          <label className="block text-sm font-medium">Monthly budget (USD)</label>
          <div className="flex gap-3">
            <input type="number" className="flex-1 border rounded-lg px-3 py-2.5 text-sm" placeholder="Min" value={data.budget_min} onChange={(e) => set("budget_min", Number(e.target.value))} />
            <input type="number" className="flex-1 border rounded-lg px-3 py-2.5 text-sm" placeholder="Max" value={data.budget_max} onChange={(e) => set("budget_max", Number(e.target.value))} />
          </div>
        </div>
      )}
      {step === 2 && (
        <Radio label="Sleep schedule" field="sleep_schedule" options={["early_bird", "night_owl", "flexible"]} value={data.sleep_schedule} onChange={(v) => set("sleep_schedule", v)} />
      )}
      {step === 3 && (
        <Radio label="Study habits" field="study_habits" options={["quiet", "moderate", "flexible"]} value={data.study_habits} onChange={(v) => set("study_habits", v)} />
      )}
      {step === 4 && (
        <Radio label="Cleanliness level" field="cleanliness" options={["high", "medium", "low"]} value={data.cleanliness} onChange={(v) => set("cleanliness", v)} />
      )}
      {step === 5 && (
        <Radio label="Guest policy" field="guests" options={["never", "rarely", "sometimes", "often"]} value={data.guests} onChange={(v) => set("guests", v)} />
      )}
      {step === 6 && (
        <Radio label="Preferred language" field="language" options={["arabic", "french", "english", "mixed"]} value={data.language} onChange={(v) => set("language", v)} />
      )}
      {step === 7 && (
        <div>
          <label className="block text-sm font-medium mb-2">Priorities (select all that apply)</label>
          {["quiet_study", "social_life", "close_to_campus", "cheap_rent", "modern_apartment"].map((p) => (
            <label key={p} className="flex items-center gap-2 py-1.5 cursor-pointer">
              <input type="checkbox" className="w-4 h-4"
                checked={data.priorities.includes(p)}
                onChange={(e) => set("priorities", e.target.checked ? [...data.priorities, p] : data.priorities.filter((x: string) => x !== p))}
              />
              <span className="text-sm capitalize">{p.replace(/_/g, " ")}</span>
            </label>
          ))}
        </div>
      )}

      <div className="flex justify-between pt-2">
        {step > 0 ? (
          <button onClick={() => setStep(step - 1)} className="px-4 py-2 border rounded-lg text-sm">Back</button>
        ) : <div />}
        {step < STEPS.length - 1 ? (
          <button onClick={() => setStep(step + 1)} className="px-6 py-2 bg-primary text-white rounded-lg text-sm">Next</button>
        ) : (
          <button onClick={submit} disabled={loading} className="px-6 py-2 bg-primary text-white rounded-lg text-sm disabled:opacity-60">
            {loading ? "Saving…" : "Finish"}
          </button>
        )}
      </div>
    </div>
  )
}

function Radio({ label, options, value, onChange }: { label: string; field: string; options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-sm font-medium mb-2">{label}</label>
      <div className="space-y-2">
        {options.map((o) => (
          <label key={o} className="flex items-center gap-2 cursor-pointer">
            <input type="radio" className="w-4 h-4" checked={value === o} onChange={() => onChange(o)} />
            <span className="text-sm capitalize">{o.replace(/_/g, " ")}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
