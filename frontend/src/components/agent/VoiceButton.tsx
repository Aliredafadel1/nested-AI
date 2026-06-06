import { useState, useRef } from "react"
import { Mic, MicOff } from "lucide-react"
import { transcribeAudio } from "../../api/agent"
import toast from "react-hot-toast"

export function VoiceButton({ onTranscript }: { onTranscript: (text: string) => void }) {
  const [recording, setRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setLoading(true)
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" })
          const text = await transcribeAudio(blob)
          if (text) onTranscript(text)
        } catch { toast.error("Transcription failed") }
        finally { setLoading(false) }
      }
      recorder.start()
      recorderRef.current = recorder
      setRecording(true)
    } catch { toast.error("Microphone access denied") }
  }

  const stop = () => {
    recorderRef.current?.stop()
    recorderRef.current = null
    setRecording(false)
  }

  return (
    <button
      onMouseDown={start} onMouseUp={stop} onTouchStart={start} onTouchEnd={stop}
      disabled={loading}
      className={`min-w-[44px] min-h-[44px] flex items-center justify-center rounded-full transition
        ${recording ? "bg-red-500 text-white animate-pulse" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}
        disabled:opacity-50`}
      title="Hold to record"
    >
      {loading ? <Mic className="w-5 h-5 animate-spin" /> :
       recording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
    </button>
  )
}
