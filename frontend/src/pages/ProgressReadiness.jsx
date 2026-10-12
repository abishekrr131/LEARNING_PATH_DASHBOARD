import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { analyticsApi } from "../api/client";

export default function ProgressReadiness() {
  const [readiness, setReadiness] = useState(null);
  const [masteryData, setMasteryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([analyticsApi.getReadiness(), analyticsApi.getMastery()])
      .then(([rData, mData]) => {
        setReadiness(rData);
        setMasteryData(mData);
      })
      .catch((err) => setError(err.message || "Failed to load readiness details"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
                Exam Readiness &amp; Progress Analytics
              </h1>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                estimate, not guarantee
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Coverage-weighted psychometric readiness index derived from Formula 17 across all curriculum skills.
            </p>
          </div>
        </div>

        {loading && (
          <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Calculating curriculum coverage and IRT parameters…</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
            {error}
          </div>
        )}

        {!loading && readiness && (
          <>
            {/* Top Readiness Score Card */}
            <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-br from-purple-900 via-indigo-900 to-gray-950 text-white shadow-xl relative overflow-hidden">
              <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 text-purple-200">
                      {readiness.target_name} Target
                    </span>
                    <span className="text-xs text-rose-300 font-medium">
                      (estimate, not guarantee)
                    </span>
                  </div>
                  <h2 className="text-4xl sm:text-5xl font-black tracking-tight text-white">
                    {readiness.readiness_percentage}%
                  </h2>
                  <p className="text-xs sm:text-sm text-purple-200 mt-2 max-w-md">
                    {readiness.is_ready ? (
                      <span className="text-emerald-400 font-semibold">
                        ✓ Readiness threshold achieved (Threshold: {Math.round(readiness.readiness_threshold * 100)}%). Continue spaced reviews to preserve retention.
                      </span>
                    ) : (
                      <span>
                        Target threshold is {Math.round(readiness.readiness_threshold * 100)}%. Gap to threshold:{" "}
                        <strong className="text-amber-300">
                          {Math.max(0, Math.round((readiness.readiness_threshold - readiness.readiness_score) * 100))}%
                        </strong>
                      </span>
                    )}
                  </p>
                </div>

                {/* Progress bar container */}
                <div className="w-full md:w-72 bg-white/10 p-4 rounded-2xl border border-white/10 backdrop-blur-sm space-y-2">
                  <div className="flex justify-between text-xs text-purple-200">
                    <span>Current Score</span>
                    <span className="font-bold">{readiness.readiness_score.toFixed(2)} / 1.00</span>
                  </div>
                  <div className="h-3 w-full bg-white/10 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-1000 ${
                        readiness.is_ready
                          ? "bg-gradient-to-r from-emerald-400 to-teal-400"
                          : "bg-gradient-to-r from-purple-400 via-indigo-400 to-rose-400"
                      }`}
                      style={{ width: `${Math.min(100, readiness.readiness_percentage)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-purple-300/80">
                    <span>Baseline (0.00)</span>
                    <span>Threshold ({readiness.readiness_threshold})</span>
                    <span>Mastery (1.00)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Formula 17 Explanation Banner */}
            <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 text-xs text-gray-600 dark:text-gray-400 space-y-1">
              <span className="font-bold text-gray-900 dark:text-white block">
                Psychometric Readiness Formulation (Formula 17):
              </span>
              <p className="font-mono text-[11px] text-purple-700 dark:text-purple-300">
                {"R = \u2211(w_s \u00B7 m_s) where m_s = (1 / |C_s|) \u2211(m_c)"}
              </p>
              <p className="text-[11px] text-gray-500">
                Each skill $s$ contributes proportionally to syllabus weight $w_s \in (0, 1]$, and concept mastery $m_c$ is derived from calibrated IRT response modeling.
              </p>
            </div>

            {/* Skill Components Breakdown */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <h3 className="font-bold text-base text-gray-900 dark:text-white">
                  Skill Mastery &amp; Weight Breakdown
                </h3>
                <span className="text-xs text-gray-400">
                  {readiness.skill_components.length} Curriculum Domains
                </span>
              </div>

              <div className="divide-y divide-gray-100 dark:divide-gray-800">
                {readiness.skill_components.map((skill) => (
                  <div
                    key={skill.skill_id}
                    className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">
                          {skill.skill_name}
                        </h4>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300">
                          Weight: {Math.round(skill.weight * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {skill.concept_count} Concepts evaluated in this domain
                      </p>
                    </div>

                    <div className="flex items-center space-x-6">
                      <div className="w-40 sm:w-48">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">Domain Mastery</span>
                          <span className="font-bold text-gray-900 dark:text-white">
                            {Math.round(skill.mean_mastery * 100)}%
                          </span>
                        </div>
                        <div className="h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              skill.mean_mastery >= 0.70
                                ? "bg-emerald-500"
                                : skill.mean_mastery >= 0.40
                                ? "bg-amber-500"
                                : "bg-rose-500"
                            }`}
                            style={{ width: `${Math.min(100, skill.mean_mastery * 100)}%` }}
                          />
                        </div>
                      </div>

                      <span
                        className={`text-xs font-bold px-2.5 py-1 rounded-lg ${
                          skill.mean_mastery >= 0.70
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                            : skill.mean_mastery >= 0.40
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                            : "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                        }`}
                      >
                        {skill.mean_mastery >= 0.70 ? "Strong" : skill.mean_mastery >= 0.40 ? "Moderate" : "Weak"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-between p-6 rounded-2xl bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/40 gap-4">
              <div>
                <h4 className="font-bold text-purple-950 dark:text-purple-200 text-sm">
                  Ready to improve your readiness score?
                </h4>
                <p className="text-xs text-purple-800/80 dark:text-purple-300/80 mt-0.5">
                  Complete targeted remediation exercises on weak concepts or take a follow-up assessment.
                </p>
              </div>

              <div className="flex items-center space-x-3 w-full sm:w-auto">
                <Link
                  to="/weak-topics"
                  className="px-4 py-2 border border-purple-300 dark:border-purple-800 text-purple-700 dark:text-purple-300 rounded-xl text-xs font-semibold hover:bg-white dark:hover:bg-gray-800 transition-colors text-center w-full sm:w-auto"
                >
                  Inspect Weak Topics
                </Link>
                <Link
                  to="/followup"
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors text-center w-full sm:w-auto"
                >
                  Take Follow-Up Test
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}
