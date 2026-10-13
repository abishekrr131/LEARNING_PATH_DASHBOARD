import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    // Clear error state and force hard navigation to bypass any stale browser memory cache
    window.location.href = window.location.origin + window.location.pathname;
  };

  handleGoDashboard = () => {
    window.location.href = "/dashboard";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-6 text-center">
          <div className="max-w-lg w-full p-8 bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-rose-200 dark:border-rose-900/60">
            <div className="w-16 h-16 bg-rose-100 dark:bg-rose-950/60 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 text-rose-600 dark:text-rose-400">
              ⚠️
            </div>
            <h2 className="text-2xl font-black text-gray-900 dark:text-white">
              Something went wrong
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 mb-6">
              The application encountered an unexpected error while rendering this page.
            </p>

            <div className="p-4 bg-rose-50/60 dark:bg-rose-950/30 rounded-xl border border-rose-100 dark:border-rose-900/40 text-left mb-6 overflow-auto max-h-40">
              <span className="text-xs font-mono font-bold text-rose-700 dark:text-rose-300 block mb-1">
                {this.state.error?.toString()}
              </span>
              {this.state.errorInfo?.componentStack && (
                <pre className="text-[10px] font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                  {this.state.errorInfo.componentStack}
                </pre>
              )}
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                type="button"
                onClick={this.handleReload}
                className="flex-1 py-3 px-4 rounded-xl font-bold text-xs bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20 transition-all"
              >
                Reload Page
              </button>
              <button
                type="button"
                onClick={this.handleGoDashboard}
                className="flex-1 py-3 px-4 rounded-xl font-bold text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 transition-all"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
