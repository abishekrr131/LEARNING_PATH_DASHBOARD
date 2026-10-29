import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { loginWithGoogle, loading } = useAuth();
  const [searchParams] = useSearchParams();
  const sessionExpired = searchParams.get("reason") === "session_expired";
  const [error, setError] = useState(null);
  const [inProgress, setInProgress] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const navigate = useNavigate();

  const handleGoogleCredential = async (idToken) => {
    if (inProgress) return;
    setError(null);
    setInProgress(true);
    setStatusMessage("Verifying your Google credentials…");

    // After 4 seconds, inform user about Render cold start
    const coldStartTimer = setTimeout(() => {
      setStatusMessage("Connecting to server… (Render free tier may take up to 45s to wake up)");
    }, 4000);

    try {
      const result = await loginWithGoogle(idToken);
      clearTimeout(coldStartTimer);

      if (result.success) {
        const hasTarget = Boolean(
          result.profile?.target_id ||
          (result.user && result.user.target_id)
        );
        if (hasTarget) {
          navigate("/dashboard");
        } else {
          navigate("/onboarding");
        }
      } else {
        setError(result.error || "Google authentication failed. Please retry.");
      }
    } catch (err) {
      clearTimeout(coldStartTimer);
      setError(err.message || "An unexpected error occurred during Google Sign-in");
    } finally {
      clearTimeout(coldStartTimer);
      setInProgress(false);
      setStatusMessage("");
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

            {/* Session Expired Banner */}
            {sessionExpired && !error && (
              <div className="mb-6 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-xs text-amber-800 dark:text-amber-300 text-center font-medium">
                🔒 Session expired, please sign in again.
              </div>
            )}

            {/* Error notice */}
            {error && (
              <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300 text-left">
                <strong>Authentication Notice:</strong> {error}
              </div>
            )}

            {/* Google Identity Services Sign-In Button */}
            <div className="w-full flex flex-col items-center justify-center space-y-3">
              <div className="w-full flex justify-center min-h-[44px]">
                <GoogleLogin
                  onSuccess={(credentialResponse) => {
                    if (credentialResponse?.credential) {
                      handleGoogleCredential(credentialResponse.credential);
                    } else {
                      setError("No credential returned by Google Identity Services.");
                    }
                  }}
                  onError={() => {
                    setError("Google Sign-In prompt was closed or failed.");
                  }}
                  text="continue_with"
                  theme="outline"
                  size="large"
                  shape="pill"
                  width="340"
                />
              </div>

              {(inProgress || loading) && (
                <div className="flex flex-col items-center justify-center space-y-1 text-xs text-purple-600 dark:text-purple-400 font-medium pt-2">
                  <div className="flex items-center space-x-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    <span>{statusMessage || "Signing in with Google…"}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Privacy & Research Telemetry Notice */}
            <div className="mt-8 pt-6 border-t border-gray-100 dark:border-gray-800">
              <p className="text-[11px] text-gray-400 dark:text-gray-500 leading-normal">
                By continuing, you participate in an adaptive psychometric learning study. Password-free authentication managed securely via Google Identity Services.
              </p>
            </div>
          </div>
      </div>
    </div>
  );
}
