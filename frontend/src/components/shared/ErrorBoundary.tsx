import { Component, ReactNode } from "react"

interface Props { children: ReactNode; title?: string }
interface State { hasError: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }
  static getDerivedStateFromError(): State { return { hasError: true } }
  handleReset = () => this.setState({ hasError: false })

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[40vh] text-center p-8">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">
            {this.props.title ?? "Something went wrong"}
          </h2>
          <p className="text-sm text-gray-500 mb-6">An unexpected error occurred.</p>
          <div className="flex gap-3">
            <button
              className="px-4 py-2 bg-primary text-white rounded-lg text-sm"
              onClick={this.handleReset}
            >
              Try again
            </button>
            <button
              className="px-4 py-2 border rounded-lg text-sm text-gray-600"
              onClick={() => window.location.reload()}
            >
              Reload page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
