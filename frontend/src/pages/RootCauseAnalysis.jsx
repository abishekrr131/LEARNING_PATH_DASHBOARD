import React, { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { analyticsApi } from "../api/client";
import MainLayout from "../layouts/MainLayout";

export default function RootCauseAnalysis() {
  const [searchParams] = useSearchParams();
  const conceptId = searchParams.get("concept_id");

  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    analyticsApi
      .getRootCauses(conceptId ? parseInt(conceptId) : null)
      .then((data) => setAnalysis(data))
      .catch((err) => setError("Failed to compute root-cause attribution."))
      .finally(() => setLoading(false));
  }, [conceptId]);

  return (
    <MainLayout currentConcept={analysis ? { id: analysis.surface_concept_id, name: analysis.surface_concept_name } : null}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 mb-2">
              ✦ Section 9 Core Contribution · Graph Attention Attribution
            </div>
            <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">
              Root-Cause Prerequisite Attribution
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Explaining <em>why</em> a concept error occurred by isolating antecedent bottleneck nodes in the 2-hop DAG.
            </p>
          </div>

          <Link
            to="/learning-path"
            className="inline-flex items-center space-x-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-purple-500/20"
          >
            <span>View Remediation on Learning Path</span>
            <span>→</span>
          </Link>
        </div>

        {/* Surface Concept Header Card */}
        {analysis && (
          <div className="p-6 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl shadow-purple-500/5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-rose-500">
                  Surface Concept Diagnosed
                </span>
                <h2 className="text-2xl font-black text-gray-900 dark:text-white mt-0.5">
                  {analysis.surface_concept_name}
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  Current Mastery:{" "}
                  <strong className="text-gray-700 dark:text-gray-300 font-mono">
                    {Math.round(analysis.surface_mastery * 100)}%
                  </strong>
                </p>
              </div>

              {/* Entropy Metric Pill */}
              <div className="p-4 rounded-2xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-right sm:min-w-[200px]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Attention Entropy H̄(c) (F8)
                </span>
                <div className="text-xl font-black text-purple-600 dark:text-purple-400 font-mono">
                  {analysis.attention_entropy}
                </div>
                <span className="text-[10px] text-gray-400">
                  Mode: <strong className="font-mono text-gray-600 dark:text-gray-300">{analysis.present_as}</strong>
                </span>
              </div>
            </div>

            {/* MANDATORY HONESTY GUARD: Present two candidates when entropy > 0.7 */}
            {analysis.present_as === "two_candidates" ? (
              <div className="mt-5 p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 text-xs text-amber-800 dark:text-amber-300 flex items-start space-x-3">
                <span className="text-xl">⚠️</span>
                <div>
                  <strong>Honesty Rule Triggered (H̄ &gt; 0.70): Presenting Alternative Candidates</strong>
                  <p className="mt-1 text-amber-700 dark:text-amber-400 leading-relaxed">
                    The model's attention distribution over the prerequisite neighborhood is diffuse (normalized Shannon entropy {analysis.attention_entropy} &gt; 0.70). Rather than asserting an overconfident single cause, the system presents the top two prerequisite candidates as alternative hypotheses.
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-5 p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 text-xs text-emerald-800 dark:text-emerald-300 flex items-start space-x-3">
                <span className="text-xl">✓</span>
                <div>
                  <strong>High Attribution Confidence (H̄ ≤ 0.70): Single Cause Isolated</strong>
                  <p className="mt-1 text-emerald-700 dark:text-emerald-400 leading-relaxed">
                    Attention concentration strongly points to a singular antecedent prerequisite node.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Candidate Prerequisite List */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-purple-100 dark:border-purple-900/40 p-6 sm:p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-base text-gray-900 dark:text-white">
              Ranked Prerequisite Ancestors (2-Hop Competency Neighborhood)
            </h3>
            <span className="text-xs text-gray-400 italic">
              {analysis?.honesty_disclaimer}
            </span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-xs text-gray-400">Enumerating graph ancestors…</div>
          ) : error ? (
            <div className="py-6 text-center text-xs text-rose-500">{error}</div>
          ) : analysis?.candidates?.length === 0 ? (
            <div className="py-8 text-center text-xs text-gray-400">
              This concept is a root node in the curriculum graph with no prior prerequisites.
            </div>
          ) : (
            <div className="space-y-4">
              {analysis?.candidates?.map((cand, idx) => {
                const isTopTwo = idx < 2 && analysis.present_as === "two_candidates";
                const isPrimary = idx === 0 && analysis.present_as === "single_cause";

                return (
                  <div
                    key={cand.candidate_concept_id}
                    className={`p-5 rounded-2xl border transition-all ${
                      isPrimary || isTopTwo
                        ? "border-purple-300 dark:border-purple-700 bg-purple-50/30 dark:bg-purple-950/20 shadow-md"
                        : "border-gray-200 dark:border-gray-800 bg-gray-50/20 dark:bg-gray-800/10"
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="flex items-start space-x-3.5">
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 ${
                            isPrimary || isTopTwo
                              ? "bg-purple-600 text-white shadow-md shadow-purple-500/30"
                              : "bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                          }`}
                        >
                          #{cand.rank}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h4 className="font-bold text-base text-gray-900 dark:text-white">
                              {cand.candidate_name}
                            </h4>
                            {isTopTwo && (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
                                Co-Candidate Alternative
                              </span>
                            )}
                            {isPrimary && (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
                                Primary Root Cause
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Direct prerequisite connected via curriculum dependency DAG.
                          </p>
                        </div>
                      </div>

                      {/* Quantitative Readouts */}
                      <div className="flex items-center space-x-6 text-xs text-right">
                        <div>
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Attention α</span>
                          <span className="font-mono font-bold text-purple-600 dark:text-purple-400 text-sm">
                            {(cand.attention_alpha * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Root Score R</span>
                          <span className="font-mono font-bold text-gray-900 dark:text-white text-sm">
                            {cand.root_score.toFixed(3)}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Mastery M_h</span>
                          <span className="font-mono font-bold text-gray-700 dark:text-gray-300 text-sm">
                            {(cand.candidate_mastery * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Error Ev</span>
                          <span className="font-mono font-bold text-rose-500 text-sm">
                            {cand.error_evidence.toFixed(2)}
                          </span>
                        </div>
                      </div>
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
