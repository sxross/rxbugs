import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
          <div className="bg-white border border-red-200 rounded-xl p-8 max-w-md w-full space-y-4">
            <h1 className="text-lg font-semibold text-red-700">Something went wrong</h1>
            <p className="text-sm text-gray-600">{this.state.error.message}</p>
            <button
              onClick={() => this.setState({ error: null })}
              className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
