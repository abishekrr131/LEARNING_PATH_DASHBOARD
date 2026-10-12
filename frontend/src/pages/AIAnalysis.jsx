import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { analyticsApi } from "../api/client";
import MainLayout from "../layouts/MainLayout";

export default function AIAnalysis() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    analyticsApi
      .getMastery()
      .then((res) => {
        setData(res);
      })
      .catch((err) => {
        setError("Failed to load mastery analytics.");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Title */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">
              AI Mastery & Model Analysis
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Latent cognitive state representations, item response calibrations, and concept mastery curves.
            </p>
          </div>

          <Link
            to="/root-cause"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20"
          >
            <span>Trace Root Causes</span>
            <span>→</span>
          </Link>
        </div>

        {/* Cold-Start Honesty Banner (MANDATORY per Spec Section 18) */}
        {data?.cold_start && (
          <div className="p-5 rounded-2xl bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-900 flex items-start space-x-3.5 shadow-sm">
            <span className="text-2xl mt-0.5">⚠️</span>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300">
                  Interface Honesty Guard: Cold-Start Mode Active
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-200 dark:bg-amber-900/60 font-mono text-amber-900 dark:text-amber-200">
                  {data.interaction_count} / 20 Interactions
                </span>
              </div>
              <p className="text-xs text-amber-700 dark:text-amber-400 mt-1 leading-relaxed">
                You have fewer than 20 recorded interactions. All concept masteries and gap scores shown on this screen are currently derived from the <strong>interpretable Formula 12 heuristic baseline</strong>. Deep neural RCT-GAT temporal representations and 2-hop attention embeddings will automatically activate once you exceed 20 interactions.
              </p>
            </div>
          </div>
        )}

        {/* Concept Mastery Grid */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-purple-100 dark:border-purple-900/40 p-6 sm:p-8">
          <h2 className="text-base font-bold text-gray-900 dark:text-white mb-4">
            Concept Mastery Matrix ({data?.concepts?.length || 0} Syllabus Nodes)
          </h2>

          {loading ? (
            <div className="py-12 text-center text-xs text-gray-400">Loading competency matrix…</div>
          ) : error ? (
            <div className="py-6 text-center text-xs text-rose-500">{error}</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data?.concepts?.map((c) => {
                const percent = Math.round(c.mastery_score * 100);
                const isWeak = c.band === "weak";
                const isMod = c.band === "moderate";

                return (
                  <div
                    key={c.concept_id}
                    className={`p-4 rounded-2xl border transition-all ${
                      isWeak
                        ? "border-rose-200 dark:border-rose-900/50 bg-rose-50/30 dark:bg-rose-950/20"
                        : isMod
                        ? "border-amber-200 dark:border-amber-900/50 bg-amber-50/20 dark:bg-amber-950/10"
                        : "border-gray-200 dark:border-gray-800 bg-gray-50/30 dark:bg-gray-800/20"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                          {c.skill_name}
                        </span>
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white mt-0.5">
                          {c.concept_name}
                        </h4>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          c.band === "strong"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                            : isMod
                            ? "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                            : "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400"
                        }`}
                      >
                        {c.band}
                      </span>
                    </div>

                    {/* Mastery Bar */}
                    <div className="mt-4">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-400 font-mono">Mastery M_c</span>
                        <span className="font-bold text-gray-700 dark:text-gray-300 font-mono">{percent}%</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            c.band === "strong"
                              ? "bg-emerald-500"
                              : isMod
                              ? "bg-amber-500"
                              : "bg-rose-500"
                          }`}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex justify-between items-center mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 text-[11px] text-gray-400">
                      <span>Confidence: {(c.confidence * 100).toFixed(0)}%</span>
                      {isWeak && (
                        <Link
                          to={`/root-cause?concept_id=${c.concept_id}`}
                          className="font-bold text-purple-600 dark:text-purple-400 hover:underline"
                        >
                          Trace Prerequisite →
                        </Link>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
