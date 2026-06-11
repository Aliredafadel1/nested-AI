import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { useUploadContract, useContract } from "../api/contracts"
import { ContractUpload } from "../components/contracts/ContractUpload"
import { RiskCard } from "../components/contracts/RiskCard"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"
import { EmptyState } from "../components/shared/EmptyState"

export function ContractsPage() {
  const { user } = useAuthStore()
  const [contractId, setContractId] = useState<number | null>(null)
  const upload = useUploadContract()
  const { data: contract } = useContract(contractId)

  if (user?.role !== "student") return <Navigate to="/listings" replace />

  const handleFile = (file: File) => {
    upload.mutate(file, {
      onSuccess: (data) => setContractId(data.contract_id),
      onError: (e: Error) => alert(e.message || "Upload failed"),
    })
  }

  const done = contract?.status === "complete"
  const failed = contract?.status === "failed"
  const analyzing = contractId && !done && !failed

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-2">Contract Analyzer</h1>
      <p className="text-sm text-gray-500 mb-6">Upload your lease PDF for AI-powered risk analysis</p>

      <ContractUpload onFile={handleFile} loading={!!analyzing || upload.isPending} />

      {analyzing && (
        <div className="mt-6 text-center">
          <LoadingSpinner />
          <p className="text-sm text-gray-500 mt-2">
            {contract?.status === "ocr_running" ? "Running OCR on scanned document…" : "Analyzing contract with AI…"}
          </p>
          <p className="text-xs text-gray-400 mt-1">This usually takes 15–30 seconds</p>
        </div>
      )}

      {failed && (
        <EmptyState
          icon="❌"
          title="Analysis failed"
          description="We could not analyze this PDF. Try a different file or a clearer scan."
          action={
            <button
              onClick={() => setContractId(null)}
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
                  onClick={() => setContractId(null)}
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
