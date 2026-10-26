import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { diagnosticApi } from "../api/client";

export default function AssessmentInstructions() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState(null);
  const [existingStatus, setExistingStatus] = useState(null);

  useEffect(() => {
    diagnosticApi.getStatus()
      .then((status) => {
        setExistingStatus(status);
        if (status?.is_completed) {
          // If already completed, user can go directly to result
        }
      })
      .catch(() => null);
  }, []);

  const handleStartDiagnostic = async () => {
    if (existingStatus?.is_completed) {
      navigate(`/result/${existingStatus.assessment_id}`);
      return;
    }
    setIsStarting(true);
    setError(null);
    const targetId = profile?.target_id || 1;

    // 30s timeout controller
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Diagnostic generation timed out after 30 seconds. Please retry.")), 30000)
    );

    try {
      const data = await Promise.race([
        diagnosticApi.start(targetId),
        timeoutPromise,
      ]);
      navigate("/diagnostic", { state: { assessment: data } });
    } catch (err) {
      console.error("Diagnostic start failed:", err);
      setError(err.message || "Failed to initialize diagnostic session. Please retry.");
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 py-12">
      <div className="max-w-xl w-full bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-purple-100 dark:border-purple-900/40 p-8 sm:p-10">
        <div className="w-12 h-12 rounded-xl bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 flex items-center justify-center font-bold text-xl mb-4">
          📝
        </div>

        <h2 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">
          Initial Diagnostic Instructions
        </h2>

        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-6">
          Target: <strong>{profile?.target_name || "Selected Curriculum"}</strong> · 10 Questions
        </p>

        <div className="space-y-4 text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
          <div className="p-4 rounded-xl bg-purple-50/50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800 flex items-start space-x-3">
            <span className="text-lg">⏱</span>
            <div>
              <strong>Response Time Recorded in Milliseconds</strong>
              <p className="mt-0.5 text-gray-500 dark:text-gray-400">
                The platform measures your exact cognitive dwell time (Formula 11). Working carefully is expected; rushing generates noise. The clock automatically pauses if you switch tabs.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-indigo-50/50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 flex items-start space-x-3">
            <span className="text-lg">⏭</span>
            <div>
              <strong>Skipping is Allowed and Informative</strong>
              <p className="mt-0.5 text-gray-500 dark:text-gray-400">
                If you do not know a concept, click <strong>Skip Question</strong>. A skip carries equal visual weight and is treated as a clean indicator of an unmet concept rather than a random guess.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 flex items-start space-x-3">
            <span className="text-lg">🔒</span>
            <div>
              <strong>Strict Progression & Autosave</strong>
              <p className="mt-0.5 text-gray-500 dark:text-gray-400">
                To guarantee zero chronological data leakage (Invariant I3), back-navigation is disabled. Your responses are committed directly to the research database upon submission.
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-6 p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-center">
            <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 mb-2">⚠️ {error}</p>
            <button
              type="button"
              onClick={handleStartDiagnostic}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all"
            >
              Retry Generation
            </button>
          </div>
        )}

        <div className="mt-8">
          <button
            type="button"
            disabled={isStarting}
            onClick={handleStartDiagnostic}
            className="w-full py-4 px-6 rounded-xl font-bold text-sm bg-gradient-to-r from-purple-600 via-indigo-600 to-rose-500 hover:from-purple-700 hover:to-rose-600 text-white shadow-xl shadow-purple-500/20 transition-all transform hover:-translate-y-0.5 disabled:opacity-50 flex items-center justify-center space-x-2"
          >
            {isStarting ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Generating your diagnostic…</span>
              </>
            ) : existingStatus?.is_completed ? (
              <span>Review Diagnostic Results (Completed ✓) →</span>
            ) : (
              <span>Start Initial Diagnostic Assessment →</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
