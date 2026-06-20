import { useEffect, useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { useUploadContract, useContract } from "../api/contracts"
import { ContractUpload } from "../components/contracts/ContractUpload"
import { RiskCard } from "../components/contracts/RiskCard"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"
import { EmptyState } from "../components/shared/EmptyState"

const STEPS = [
  { label: "Uploading PDF to secure storage…",   minMs: 0    },
  { label: "Reading contract text…",              minMs: 2000 },
  { label: "Screening clauses for risk…",         minMs: 6000 },
  { label: "Running deep AI analysis…",           minMs: 12000},
  { label: "Almost done — writing your report…",  minMs: 26000},
]

export function ContractsPage() {
  const { user } = useAuthStore()
  const [contractId, setContractId]   = useState<number | null>(null)
  const [startedAt,  setStartedAt]    = useState<number | null>(null)
  const [stepIdx,    setStepIdx]      = useState(0)
  const upload   = useUploadContract()
  const { data: contract, isError } = useContract(contractId)

  if (user?.role !== "student") return <Navigate to="/listings" replace />

  const handleFile = (file: File) => {
    setStepIdx(0)
    setStartedAt(Date.now())
    upload.mutate(file, {
      onSuccess: (data) => setContractId(data.contract_id),
      onError:   (e: Error) => alert(e.message || "Upload failed"),
    })
  }

  const done     = contract?.status === "complete"
  const failed   = contract?.status === "failed" || isError
  const analyzing = contractId && !done && !failed

  useEffect(() => {
    if (!analyzing || startedAt === null) return
    const interval = setInterval(() => {
      const elapsed = Date.now() - startedAt
      const next = STEPS.findIndex((s, i) => i > stepIdx && elapsed >= s.minMs)
      if (next !== -1) setStepIdx(next)
    }, 500)
    return () => clearInterval(interval)
  }, [analyzing, startedAt, stepIdx])

  const ocrRunning = contract?.status === "ocr_running"
  const currentLabel = ocrRunning
    ? "Running OCR on scanned document…"
    : STEPS[stepIdx]?.label ?? STEPS[STEPS.length - 1].label
  const progressPct = Math.min(100, ((stepIdx + 1) / STEPS.length) * 100)

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-2">Contract Analyzer</h1>
      <p className="text-sm text-gray-500 mb-6">Upload your lease PDF for AI-powered risk analysis</p>

      <ContractUpload onFile={handleFile} loading={!!analyzing || upload.isPending} />

      {analyzing && (
        <div className="mt-6 space-y-4">
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <LoadingSpinner />
              <p className="text-sm font-medium text-blue-800">{currentLabel}</p>
            </div>
            <div className="w-full bg-blue-100 rounded-full h-1.5">
              <div
                className="bg-blue-500 h-1.5 rounded-full transition-all duration-700"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <p className="text-xs text-blue-500 mt-2 text-right">
              This usually takes 25–35 seconds
            </p>
          </div>
          <div className="space-y-1">
            {STEPS.map((s, i) => (
              <div key={i} className={`flex items-center gap-2 text-xs px-1 transition-opacity duration-300 ${i <= stepIdx ? "opacity-100" : "opacity-30"}`}>
                <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${i < stepIdx ? "bg-green-100 text-green-600" : i === stepIdx ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-400"}`}>
                  {i < stepIdx ? "✓" : i + 1}
                </span>
                <span className={i < stepIdx ? "text-green-600" : i === stepIdx ? "text-blue-700 font-medium" : "text-gray-400"}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {failed && (
        <EmptyState
          icon="❌"
          title="Analysis failed"
          description="We could not analyze this PDF. Make sure it is not password-protected, then try again."
          action={
            <button
              onClick={() => { setContractId(null); setStartedAt(null); setStepIdx(0) }}
              className="px-4 py-2 bg-primary text-white rounded-lg text-sm"
            >
              Try another file
            </button>
          }
        />
      )}

      {done && contract?.analysis && (
        <div className="mt-6 space-y-3">
          {contract.ocr_used && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-700">
              📷 Scanned document — OCR used. Results may vary based on scan quality.
            </div>
          )}

          {contract.analysis.risk_items.length === 0 ? (
            <EmptyState
              icon="✅"
              title="No risk items found"
              description="This contract looks clean. Always read through it yourself before signing."
            />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-sm text-gray-700">
                  {contract.analysis.risk_items.length} risk item{contract.analysis.risk_items.length !== 1 ? "s" : ""} found
                </h2>
                <button
                  onClick={() => { setContractId(null); setStartedAt(null); setStepIdx(0) }}
                  className="text-xs text-gray-400 hover:text-gray-600 underline"
                >
                  Analyze another
                </button>
              </div>
              {contract.analysis.risk_items.map((item, i) => <RiskCard key={i} item={item} />)}
            </>
          )}
        </div>
      )}
    </div>
  )
}
