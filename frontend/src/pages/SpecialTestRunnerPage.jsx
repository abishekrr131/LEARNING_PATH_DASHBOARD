import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { assessmentApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import SpecialTestRunner from "../components/SpecialTestRunner";

export default function SpecialTestRunnerPage() {
  const { profile } = useAuth();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mainCount, setMainCount] = useState(5);
  const [hasStarted, setHasStarted] = useState(false);

  const startTest = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await assessmentApi.start({
        type: "special",
        target_id: profile?.target_id || 1,
        main_count: mainCount,
      });
      setAssessment(data);
      setHasStarted(true);
    } catch (err) {
      setError(err.message || "Failed to initialize special timed assessment session.");
    } finally {
      setLoading(false);
    }
  };

  const handleFinished = (finalSummary) => {
    navigate(`/result/${finalSummary.assessment_id}`, {
      state: {
        result: {
          assessment_id: finalSummary.assessment_id,
          score: finalSummary.score,
          accuracy: finalSummary.accuracy,
          total_questions: finalSummary.total_answered,
          correct_count: finalSummary.correct_count,
          summary: `Completed Special Timed Test with ${finalSummary.timed_out_count} timeouts and ${finalSummary.skip_count} skips.`,
        },
      },
    });
  };

  if (!hasStarted) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex items-center justify-center p-4 sm:p-6">
        <div className="max-w-xl w-full bg-white dark:bg-gray-900 rounded-3xl p-6 sm:p-8 border border-gray-100 dark:border-gray-800 shadow-xl space-y-6">
          <div className="text-center space-y-2">
            <span className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-rose-500 to-amber-500 text-white text-2xl flex items-center justify-center mx-auto shadow-md shadow-rose-500/20">
              ⚡
            </span>
            <h1 className="text-2xl font-black text-gray-900 dark:text-white">
              Special Timed Test Mode
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              High-velocity adaptive test designed to expose cognitive prerequisite vulnerabilities under time pressure.
            </p>
          </div>

          <div className="space-y-3 bg-purple-50/50 dark:bg-purple-950/20 p-4 rounded-2xl border border-purple-100 dark:border-purple-900/40 text-xs text-gray-700 dark:text-gray-300">
            <h3 className="font-bold text-purple-900 dark:text-purple-200">How this timed mode functions:</h3>
            <ul className="list-disc list-inside space-y-1.5 text-gray-600 dark:text-gray-400">
              <li><strong>Main Questions:</strong> 30-second hard limit per question.</li>
              <li><strong>Dynamic Sub-Questions:</strong> 3 sub-questions per block with a 20-second hard limit each.</li>
              <li><strong>Root-Cause Routing:</strong> Sub-questions automatically branch to upstream 1–2 hop prerequisite concepts if the main question is missed.</li>
              <li><strong>Timeout Handling:</strong> When the countdown ring expires, questions auto-submit as <span className="text-rose-600 font-mono">timed_out</span>.</li>
              <li><strong>Strict Integrity:</strong> Gemini AI Assistant is deactivated for the duration. Leaving the page triggers automatic timeout.</li>
            </ul>
          </div>

          {/* Block Selection */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-700 dark:text-gray-300 block">
              Choose Test Length:
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMainCount(5)}
                className={`p-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                  mainCount === 5
                    ? "border-purple-600 bg-purple-50 text-purple-900 dark:bg-purple-950/60 dark:text-purple-200"
                    : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400"
                }`}
              >
                5 Main Blocks (20 total items)
                <span className="block text-[10px] text-gray-400 font-normal mt-0.5">~7.5 mins total</span>
              </button>
              <button
                type="button"
                onClick={() => setMainCount(10)}
                className={`p-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                  mainCount === 10
                    ? "border-purple-600 bg-purple-50 text-purple-900 dark:bg-purple-950/60 dark:text-purple-200"
                    : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400"
                }`}
              >
                10 Main Blocks (40 total items)
                <span className="block text-[10px] text-gray-400 font-normal mt-0.5">~15 mins total</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-xs">
              {error}
            </div>
          )}

          <div className="flex items-center space-x-3 pt-2">
            <button
              type="button"
              onClick={() => navigate("/assessments")}
              className="w-1/3 py-3 border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 rounded-xl text-xs font-semibold hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={startTest}
              className="w-2/3 py-3 bg-gradient-to-r from-rose-500 to-amber-500 hover:from-rose-600 hover:to-amber-600 text-white rounded-xl text-xs font-bold shadow-lg shadow-rose-500/20 transition-all flex items-center justify-center space-x-2"
            >
              {loading ? (
                <span>Initializing Blocks…</span>
              ) : (
                <span>Begin Timed Assessment →</span>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 py-10 px-4">
      <SpecialTestRunner
        assessmentId={assessment.assessment_id}
        initialItems={assessment.items}
        totalMainCount={mainCount}
        onFinished={handleFinished}
      />
    </div>
  );
}
