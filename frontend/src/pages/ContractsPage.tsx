import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { Navigate } from "react-router-dom"
import { useUploadContract, useContract } from "../api/contracts"
import { ContractUpload } from "../components/contracts/ContractUpload"
import { RiskCard } from "../components/contracts/RiskCard"
import { LoadingSpinner } from "../components/shared/LoadingSpinner"

export function ContractsPage() {
  const { user } = useAuthStore()
  if (user?.role !== "student") return <Navigate to="/listings" replace />

  const [contractId, setContractId] = useState<number | null>(null)
  const upload = useUploadContract()
  const { data: contract } = useContract(contractId)

  const handleFile = (file: File) => {
    upload.mutate(file, {
      onSuccess: (data) => setContractId(data.contract_id),
      onError: (e: any) => alert(e.message || "Upload failed"),
    })
  }

  const done = contract?.status === "complete"
  const failed = contract?.status === "failed"
  const loading = contractId && !done && !failed

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-2">Contract Analyzer</h1>
      <p className="text-sm text-gray-500 mb-6">Upload your lease PDF for AI-powered risk analysis</p>

      <ContractUpload onFile={handleFile} loading={!!loading || upload.isPending} />

      {loading && (
        <div className="mt-6 text-center">
          <LoadingSpinner />
          <p className="text-sm text-gray-500 mt-2">
            {contract?.status === "ocr_running" ? "Running OCR…" : "Analyzing contract…"}
          </p>
        </div>
      )}

      {failed && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
          Analysis failed. Please try again with a different PDF.
        </div>
      )}

      {done && contract?.analysis && (
        <div className="mt-6 space-y-3">
          {contract.ocr_used && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-700">
              📷 Scanned document — OCR used
            </div>
          )}
          <h2 className="font-semibold text-sm text-gray-700">
            {contract.analysis.risk_items.length} risk items found
          </h2>
          {contract.analysis.risk_items.map((item, i) => <RiskCard key={i} item={item} />)}
        </div>
      )}
    </div>
  )
}
