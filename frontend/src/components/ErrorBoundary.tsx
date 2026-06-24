import { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-night-950 text-mist-200 p-6 text-center">
          <div className="bg-night-800/50 border border-night-600 rounded-card p-8 max-w-lg shadow-2xl backdrop-blur-md">
            <AlertTriangle className="w-12 h-12 text-aqi-usg mx-auto mb-4 opacity-80" />
            <h1 className="font-display text-2xl font-bold text-mist-100 mb-2">
              The Atmosphere scattered
            </h1>
            <p className="text-mist-400 mb-6 leading-relaxed">
              We encountered an unexpected visual rendering error. The map canvas failed to draw the current atmosphere.
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="px-6 py-2.5 bg-clean-400 text-night-950 font-medium rounded-full hover:bg-clean-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-clean-400 focus-visible:ring-offset-night-900"
            >
              Reload Explorer
            </button>
            <p className="mt-6 text-xs text-night-500 font-mono">
              {this.state.error?.message}
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
