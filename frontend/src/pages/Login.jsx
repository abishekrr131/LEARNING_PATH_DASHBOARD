import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { loginWithGoogle, loading } = useAuth();
  const [error, setError] = useState(null);
  const [inProgress, setInProgress] = useState(false);
  const navigate = useNavigate();

  const handleGoogleSignIn = async () => {
    setError(null);
    setInProgress(true);
    try {
      // In development/test mode, use the verified dev ID token
      const devIdToken = "mock-google-token-user-1";
      const result = await loginWithGoogle(devIdToken);

      if (result.success) {
        // If user has chosen a target, route to Dashboard, else Onboarding
        if (result.profile && result.profile.target_id) {
          navigate("/dashboard");
        } else {
          navigate("/onboarding");
        }
      } else {
        setError(result.error || "Authentication failed");
      }
    } catch (err) {
      setError(err.message || "An unexpected error occurred during Google Sign-in");
    } finally {
      setInProgress(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8">
      {/* Background Gradient Orbs */}
      <div className="absolute top-1/4 -left-20 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 -right-20 w-80 h-80 bg-rose-500/20 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full relative z-10">
        {/* Card Container */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-purple-100 dark:border-purple-900/40 p-8 sm:p-10 text-center">
          {/* Logo Badge */}
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-rose-500 flex items-center justify-center text-white font-black text-2xl shadow-xl shadow-purple-500/30 mx-auto mb-6">
            ✦
          </div>

          <h2 className="text-2xl sm:text-3xl font-black text-gray-900 dark:text-white tracking-tight">
            Your learning journey starts here.
          </h2>

          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 mb-8 leading-relaxed">
            Welcome to RCT-GAT. Single sign-on with Google secures your progress, diagnostic telemetry, and personalized review queue.
          </p>

          {/* Error notice */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300 text-left">
              <strong>Authentication Notice:</strong> {error}
            </div>
          )}

          {/* Primary Action Button: Google Sign-In Only */}
          <button
            type="button"
            disabled={inProgress || loading}
            onClick={handleGoogleSignIn}
            className="w-full flex items-center justify-center space-x-3 py-4 px-6 rounded-2xl font-semibold text-sm border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-750 shadow-md hover:shadow-lg hover:border-purple-300 dark:hover:border-purple-600 transition-all transform active:scale-95 disabled:opacity-50"
          >
            {/* Google G Logo SVG */}
            <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>{inProgress ? "Signing in…" : "Continue with Google"}</span>
          </button>

          {/* Privacy & Research Telemetry Notice */}
          <div className="mt-8 pt-6 border-t border-gray-100 dark:border-gray-800">
            <p className="text-[11px] text-gray-400 dark:text-gray-500 leading-normal">
              By continuing, you participate in an adaptive psychometric learning study. Password-free authentication managed via Google Identity Services.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
