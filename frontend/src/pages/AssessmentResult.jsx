import React from "react";
import { useLocation, useNavigate, useParams, Link } from "react-router-dom";

export default function AssessmentResult() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;

  if (!result) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <h3 className="font-bold text-gray-900 dark:text-white">Assessment Complete</h3>
        <p className="text-xs text-gray-500 mt-2 mb-4">Results have been registered to your profile.</p>
        <Link to="/dashboard" className="px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-semibold">
          Go to Dashboard →
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 py-12 px-4 sm:px-6">
      <div className="max-w-3xl mx-auto bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-purple-100 dark:border-purple-900/40 p-8 sm:p-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/40 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-3 shadow-md shadow-purple-500/10">
            📊
          </div>
          <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
            Assessment Completed · Session #{id}
          </span>
          <h2 className="text-3xl font-black text-gray-900 dark:text-white mt-1">Diagnostic Results</h2>
        </div>

        {/* Top Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <div className="p-4 rounded-2xl bg-purple-50/60 dark:bg-purple-950/30 border border-purple-100 dark:border-purple-800 text-center">
            <span className="text-xs text-gray-500 dark:text-gray-400">Overall Score</span>
            <div className="text-2xl font-black text-purple-600 dark:text-purple-400 mt-1">
              {result.score}%
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800 text-center">
            <span className="text-xs text-gray-500 dark:text-gray-400">Correct Items</span>
            <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
              {result.correct_count} / {result.total_questions}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/30 border border-amber-100 dark:border-amber-800 text-center">
            <span className="text-xs text-gray-500 dark:text-gray-400">Skips</span>
            <div className="text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">
              {result.skip_count}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-800 text-center">
            <span className="text-xs text-gray-500 dark:text-gray-400">Time Ratio (F11)</span>
            <div className="text-2xl font-black text-indigo-600 dark:text-indigo-400 mt-1">
              {result.mean_time_ratio}x
            </div>
          </div>
        </div>

        {/* Per-Concept Performance Breakdown */}
        <div className="mb-8">
          <h3 className="font-bold text-sm text-gray-900 dark:text-white uppercase tracking-wider mb-3">
            Concept Diagnostics & Formula 12 Gap Scores
          </h3>

          <div className="border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-300">Concept</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-600 dark:text-gray-300">Accuracy</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-600 dark:text-gray-300">Time Ratio</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-600 dark:text-gray-300">Skip Rate</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-600 dark:text-gray-300">Gap Score</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-600 dark:text-gray-300">Band</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {result.per_concept?.map((c) => (
                  <tr key={c.concept_id} className="hover:bg-purple-50/30 dark:hover:bg-purple-900/10">
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{c.concept_name}</td>
                    <td className="px-4 py-3 text-center font-mono">{(c.accuracy * 100).toFixed(0)}%</td>
                    <td className="px-4 py-3 text-center font-mono">{c.mean_time_ratio.toFixed(2)}x</td>
                    <td className="px-4 py-3 text-center font-mono">{(c.skip_rate * 100).toFixed(0)}%</td>
                    <td className="px-4 py-3 text-center font-mono font-bold text-purple-600 dark:text-purple-400">
                      {c.gap_score.toFixed(3)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          c.band === "strong"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                            : c.band === "moderate"
                            ? "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                            : "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400"
                        }`}
                      >
                        {c.band}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => navigate("/ai-analysis")}
            className="py-3.5 px-6 rounded-xl font-bold text-sm bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-lg shadow-purple-500/20 text-center"
          >
            View AI Analysis & Cold-Start Mode →
          </button>
          <button
            type="button"
            onClick={() => navigate("/dashboard")}
            className="py-3.5 px-6 rounded-xl font-bold text-sm border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 text-center"
          >
            Go to Student Dashboard →
          </button>
        </div>
      </div>
    </div>
  );
}
