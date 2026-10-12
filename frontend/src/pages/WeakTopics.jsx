import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { analyticsApi } from "../api/client";
import MainLayout from "../layouts/MainLayout";

export default function WeakTopics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterBand, setFilterBand] = useState("all");

  useEffect(() => {
    analyticsApi
      .getGaps()
      .then((res) => setData(res))
      .catch(() => setData({ gaps: [] }))
      .finally(() => setLoading(false));
  }, []);

  const gaps = data?.gaps || [];
  const filtered = gaps.filter((g) => {
    if (filterBand === "all") return true;
    return g.band === filterBand;
  });

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">
              Skill Gap & Weak Topics Analysis
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Decomposed components of Formula 12 (interpretable severity score) and Formula 14 adaptive queue priority.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <span className="text-gray-400">Filter Band:</span>
            {["all", "weak", "moderate", "strong"].map((b) => (
              <button
                key={b}
                onClick={() => setFilterBand(b)}
                className={`px-3 py-1.5 rounded-lg font-bold capitalize transition-all ${
                  filterBand === b
                    ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                    : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400"
                }`}
              >
                {b}
              </button>
            ))}
          </div>
        </div>

        {/* Formula Explanation Callout */}
        <div className="p-4 rounded-2xl bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-800 text-xs text-gray-700 dark:text-gray-300">
          <strong>Formula 12 Formulation:</strong>{" "}
          <code className="font-mono text-purple-700 dark:text-purple-300">
            G_c = 0.40·(1 - Accuracy) + 0.20·TimePenalty + 0.20·SkipRate + 0.20·(1 - M_hist)
          </code>
          <p className="mt-1 text-[11px] text-gray-400">
            Bands: &lt;0.30 strong · 0.30–0.60 moderate (eligible for verification probe) · &gt;0.60 weak (priority remediation).
          </p>
        </div>

        {/* Table of Gaps */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-purple-100 dark:border-purple-900/40 overflow-hidden">
          {loading ? (
            <div className="py-12 text-center text-xs text-gray-400">Computing gap matrix…</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-400">No concepts match the selected filter.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-xs">
                <thead className="bg-gray-50/70 dark:bg-gray-800/50">
                  <tr>
                    <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Concept</th>
                    <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Skill Domain</th>
                    <th className="px-5 py-3.5 text-center font-semibold text-gray-600 dark:text-gray-300">Accuracy</th>
                    <th className="px-5 py-3.5 text-center font-semibold text-gray-600 dark:text-gray-300">Time Ratio</th>
                    <th className="px-5 py-3.5 text-center font-semibold text-gray-600 dark:text-gray-300">Skip Rate</th>
                    <th className="px-5 py-3.5 text-center font-semibold text-gray-600 dark:text-gray-300">Hist Mastery</th>
                    <th className="px-5 py-3.5 text-center font-semibold text-purple-600 dark:text-purple-400">Gap Score G_c</th>
                    <th className="px-5 py-3.5 text-center font-semibold text-gray-600 dark:text-gray-300">Band</th>
                    <th className="px-5 py-3.5 text-center font-semibold text-indigo-600 dark:text-indigo-400">F14 Priority</th>
                    <th className="px-5 py-3.5 text-right font-semibold text-gray-600 dark:text-gray-300">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {filtered.map((g) => (
                    <tr key={g.concept_id} className="hover:bg-purple-50/20 dark:hover:bg-purple-900/10">
                      <td className="px-5 py-4 font-bold text-gray-900 dark:text-white">{g.concept_name}</td>
                      <td className="px-5 py-4 text-gray-500 dark:text-gray-400">{g.skill_name}</td>
                      <td className="px-5 py-4 text-center font-mono">{(g.accuracy * 100).toFixed(0)}%</td>
                      <td className="px-5 py-4 text-center font-mono">{g.time_ratio.toFixed(2)}x</td>
                      <td className="px-5 py-4 text-center font-mono">{(g.skip_rate * 100).toFixed(0)}%</td>
                      <td className="px-5 py-4 text-center font-mono">{g.historical_mastery.toFixed(2)}</td>
                      <td className="px-5 py-4 text-center font-mono font-bold text-purple-600 dark:text-purple-400">
                        {g.gap_score.toFixed(3)}
                      </td>
                      <td className="px-5 py-4 text-center">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            g.band === "strong"
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                              : g.band === "moderate"
                              ? "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                              : "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400"
                          }`}
                        >
                          {g.band}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-center font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        {g.priority.toFixed(4)}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Link
                          to={`/root-cause?concept_id=${g.concept_id}`}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:bg-purple-600 hover:text-white transition-all"
                        >
                          Trace Cause →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
