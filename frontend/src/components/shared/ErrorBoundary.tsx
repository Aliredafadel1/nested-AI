import { Component, ReactNode } from "react"

interface State { hasError: boolean }

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[40vh] text-center p-8">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">Something went wrong</h2>
          <button
            className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm"
            onClick={() => window.location.reload()}
          >
            Refresh the page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
