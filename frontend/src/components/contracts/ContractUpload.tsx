import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { Upload } from "lucide-react"

interface Props { onFile: (file: File) => void; loading: boolean }

export function ContractUpload({ onFile, loading }: Props) {
  const [file, setFile] = useState<File | null>(null)

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) {
      setFile(accepted[0])
      onFile(accepted[0])
    }
  }, [onFile])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { "application/pdf": [".pdf"] }, maxFiles: 1, disabled: loading,
  })

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition
          ${isDragActive ? "border-primary bg-primary/5" : "border-gray-300 hover:border-primary/50"}
          ${loading ? "opacity-60 cursor-not-allowed" : ""}`}
      >
        <input {...getInputProps()} />
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-600">
          {isDragActive ? "Drop your PDF here" : "Drag & drop a PDF, or click to browse"}
        </p>
        <p className="text-xs text-gray-400 mt-1">Max 10 MB · PDF only — analysis starts automatically</p>
      </div>
      {file && (
        <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
          <span className="text-sm text-gray-700">📄 {file.name}</span>
          {loading && <span className="text-xs text-gray-400">Analyzing…</span>}
        </div>
      )}
    </div>
  )
}
