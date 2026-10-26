import React, { useState, useEffect, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { analyticsApi } from "../api/client";
import MainLayout from "../layouts/MainLayout";

export default function RootCauseAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const conceptId = searchParams.get("concept_id");

  const [analysis, setAnalysis] = useState(null);
  const [weeklyData, setWeeklyData] = useState(null);
  const [refreshingWeekly, setRefreshingWeekly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Concept Selector state
  const [conceptFilter, setConceptFilter] = useState("all"); // 'weak' | 'all'
  const [conceptSearch, setConceptSearch] = useState("");

  const fetchAnalysis = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      analyticsApi.getRootCauses(conceptId ? parseInt(conceptId) : null),
      analyticsApi.getWeeklySnapshots().catch(() => null),
    ])
      .then(([rootCauseData, weekly]) => {
        setAnalysis(rootCauseData);
        if (weekly) setWeeklyData(weekly);
      })
      .catch((err) => setError("Failed to compute root-cause attribution."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAnalysis();
  }, [conceptId]);

  const handleManualWeeklyRefresh = async () => {
    setRefreshingWeekly(true);
    try {
      const updated = await analyticsApi.refreshWeekly();
      setWeeklyData(updated);
      const rc = await analyticsApi.getRootCauses(conceptId ? parseInt(conceptId) : null);
      setAnalysis(rc);
    } catch (e) {
      console.error("Weekly refresh failed", e);
    } finally {
      setRefreshingWeekly(false);
    }
  };

  const handleSelectConcept = (newConceptId) => {
    setSearchParams({ concept_id: String(newConceptId) });
  };

  const getErrorTypeBadgeColor = (errorType) => {
    switch (errorType) {
      case "arithmetic_or_calculation_error":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800";
      case "incorrect_formula_or_rule":
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800";
      case "missing_prerequisite_knowledge":
        return "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800";
      case "conceptual_misunderstanding":
        return "bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border-red-200 dark:border-red-800";
      case "time_pressure_or_careless_error":
        return "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800";
      case "question_misinterpretation":
        return "bg-orange-100 text-orange-800 dark:bg-orange-950/60 dark:text-orange-300 border-orange-200 dark:border-orange-800";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700";
    }
  };

  const remediationTargetUrl = analysis?.remediation_concept_id
    ? `/learning-path?concept_id=${analysis.remediation_concept_id}`
    : "/learning-path";

  // Filtered concepts for dropdown
  const filteredConcepts = useMemo(() => {
    if (!analysis?.target_concepts) return [];
    let list = analysis.target_concepts;
    if (conceptFilter === "weak") {
      list = list.filter((c) => c.is_weak || c.mistakes_count > 0);
    }
    if (conceptSearch.trim()) {
      const q = conceptSearch.toLowerCase();
      list = list.filter(
        (c) =>
          c.concept_name.toLowerCase().includes(q) ||
          c.topic_name.toLowerCase().includes(q)
      );
    }
    return list;
  }, [analysis?.target_concepts, conceptFilter, conceptSearch]);

  const weakCount = useMemo(() => {
    if (!analysis?.target_concepts) return 0;
    return analysis.target_concepts.filter((c) => c.is_weak || c.mistakes_count > 0).length;
  }, [analysis?.target_concepts]);

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
            to={remediationTargetUrl}
            className="inline-flex items-center space-x-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-purple-500/20"
          >
            <span>View Remediation on Learning Path</span>
            <span>→</span>
          </Link>
        </div>

        {/* Interactive Concept Selector Card */}
        {analysis?.target_concepts && analysis.target_concepts.length > 0 && (
          <div className="p-5 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-lg space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                  Target Curriculum: {analysis.target_name || "Active Track"}
                </span>
                <h3 className="text-sm font-bold text-gray-900 dark:text-white mt-0.5">
                  Select Concept to Diagnose
                </h3>
              </div>

              {/* Filter Pills */}
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setConceptFilter("weak")}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                    conceptFilter === "weak"
                      ? "bg-rose-500 text-white shadow-sm shadow-rose-500/30"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                  }`}
                >
                  Weak Concepts ({weakCount})
                </button>
                <button
                  type="button"
                  onClick={() => setConceptFilter("all")}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                    conceptFilter === "all"
                      ? "bg-purple-600 text-white shadow-sm shadow-purple-500/30"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                  }`}
                >
                  All Concepts ({analysis.target_concepts.length})
                </button>
              </div>
            </div>

            {/* Select Input with Search */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              <div className="sm:col-span-2">
                <select
                  value={analysis.surface_concept_id || ""}
                  onChange={(e) => handleSelectConcept(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-semibold rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {filteredConcepts.map((c) => (
                    <option key={c.concept_id} value={c.concept_id}>
                      {c.topic_name} → {c.concept_name} (Mastery: {Math.round(c.mastery * 100)}%
                      {c.mistakes_count > 0 ? ` • ${c.mistakes_count} mistake(s)` : ""})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <input
                  type="text"
                  placeholder="Filter by concept name..."
                  value={conceptSearch}
                  onChange={(e) => setConceptSearch(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>
          </div>
        )}

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
                  {" • "}
                  Status:{" "}
                  <span className="font-semibold text-purple-600 dark:text-purple-400">
                    {analysis.attribution_state === "valid_attribution"
                      ? "Graph Attribution Verified"
                      : analysis.attribution_state === "no_valid_prerequisites"
                      ? "Foundational Root Node (0 Prerequisites)"
                      : analysis.attribution_state === "missing_graph_mapping"
                      ? "Unmapped Curriculum Concept"
                      : "Insufficient Attempt Evidence"}
                  </span>
                </p>
              </div>

              {/* Entropy Metric Pill */}
              <div className="p-4 rounded-2xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-right sm:min-w-[220px]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Attention Entropy H̄(c) (F8)
                </span>
                <div className="text-xl font-black text-purple-600 dark:text-purple-400 font-mono">
                  {analysis.attention_entropy !== null && analysis.attention_entropy !== undefined
                    ? analysis.attention_entropy
                    : "N/A"}
                </div>
                <span className="text-[10px] text-gray-400">
                  Mode:{" "}
                  <strong className="font-mono text-gray-600 dark:text-gray-300">
                    {analysis.attribution_state === "valid_attribution"
                      ? analysis.present_as
                      : analysis.attribution_state === "no_valid_prerequisites"
                      ? "root_node"
                      : analysis.attribution_state === "missing_graph_mapping"
                      ? "unmapped"
                      : "inconclusive"}
                  </strong>
                </span>
              </div>
            </div>

            {/* Attribution State & Honesty Guard Banners */}
            {analysis.attribution_state === "valid_attribution" ? (
              analysis.present_as === "two_candidates" ? (
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
                    <strong>High Attribution Confidence (H̄ ≤ 0.70): Single Bottleneck Isolated</strong>
                    <p className="mt-1 text-emerald-700 dark:text-emerald-400 leading-relaxed">
                      Attention concentration strongly points to a singular antecedent prerequisite node.
                    </p>
                  </div>
                </div>
              )
            ) : analysis.attribution_state === "no_valid_prerequisites" ? (
              <div className="mt-5 p-4 rounded-2xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 text-xs text-blue-800 dark:text-blue-300 flex items-start space-x-3">
                <span className="text-xl">ℹ️</span>
                <div>
                  <strong>Curriculum Graph Verified: Foundational Root Node</strong>
                  <p className="mt-1 text-blue-700 dark:text-blue-400 leading-relaxed">
                    "{analysis.surface_concept_name}" has no prior prerequisite predecessors in the syllabus DAG. All foundational knowledge begins at this node; remediation directs study directly to this concept.
                  </p>
                </div>
              </div>
            ) : analysis.attribution_state === "missing_graph_mapping" ? (
              <div className="mt-5 p-4 rounded-2xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs text-gray-700 dark:text-gray-300 flex items-start space-x-3">
                <span className="text-xl">⚙️</span>
                <div>
                  <strong>Graph Mapping Notice: Isolated / Unmapped Concept</strong>
                  <p className="mt-1 text-gray-600 dark:text-gray-400 leading-relaxed">
                    This concept does not have prerequisite dependencies mapped in the current curriculum graph.
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-5 p-4 rounded-2xl bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900 text-xs text-purple-800 dark:text-purple-300 flex items-start space-x-3">
                <span className="text-xl">📊</span>
                <div>
                  <strong>Awaiting Empirical Error Calibration</strong>
                  <p className="mt-1 text-purple-700 dark:text-purple-400 leading-relaxed">
                    No failed question attempts recorded for this concept. Further practice drills will calibrate prerequisite attribution.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Visual Prerequisite DAG Progression Breadcrumb */}
        {analysis && (analysis.direct_prerequisites?.length > 0 || analysis.direct_dependents?.length > 0) && (
          <div className="p-5 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-lg space-y-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
              ✦ Directed Curriculum Progression (DAG Slice)
            </span>
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
              {/* Direct Prerequisites */}
              {analysis.direct_prerequisites && analysis.direct_prerequisites.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1.5">
                  {analysis.direct_prerequisites.map((p) => (
                    <button
                      key={p.concept_id}
                      onClick={() => handleSelectConcept(p.concept_id)}
                      className="px-3 py-1.5 rounded-xl font-bold bg-amber-50 dark:bg-amber-950/40 hover:bg-amber-100 dark:hover:bg-amber-900/50 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 transition-all flex items-center space-x-1"
                      title="Click to diagnose this prerequisite"
                    >
                      <span>← {p.concept_name}</span>
                      <span className="text-[10px] font-mono opacity-75 font-normal">
                        ({Math.round(p.mastery * 100)}%)
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <span className="text-gray-400 italic text-[11px]">
                  [Foundational Root Node]
                </span>
              )}

              <span className="text-purple-400 dark:text-purple-500 font-bold px-1">➔</span>

              {/* Surface Concept Node */}
              <div className="px-3.5 py-1.5 rounded-xl font-bold bg-purple-600 text-white shadow-md shadow-purple-500/20">
                ★ {analysis.surface_concept_name} ({Math.round(analysis.surface_mastery * 100)}%)
              </div>

              <span className="text-purple-400 dark:text-purple-500 font-bold px-1">➔</span>

              {/* Downstream Applications */}
              {analysis.direct_dependents && analysis.direct_dependents.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1.5">
                  {analysis.direct_dependents.map((d) => (
                    <button
                      key={d.concept_id}
                      onClick={() => handleSelectConcept(d.concept_id)}
                      className="px-3 py-1.5 rounded-xl font-bold bg-indigo-50 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 transition-all flex items-center space-x-1"
                      title="Click to diagnose downstream dependent"
                    >
                      <span>{d.concept_name} →</span>
                      <span className="text-[10px] font-mono opacity-75 font-normal">
                        ({Math.round(d.mastery * 100)}%)
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <span className="text-gray-400 italic text-[11px]">
                  [Advanced Terminal Concept]
                </span>
              )}
            </div>
          </div>
        )}

        {/* Detailed Mistake Evidence & Question Breakdown */}
        {analysis?.recent_mistakes && analysis.recent_mistakes.length > 0 && (
          <div className="p-6 rounded-3xl bg-white dark:bg-gray-900 border border-rose-100 dark:border-rose-900/40 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-rose-500">
                  ✦ Empirical Question Mistake Evidence
                </span>
                <h3 className="text-lg font-black text-gray-900 dark:text-white mt-0.5">
                  Recent Question Mistakes on {analysis.surface_concept_name}
                </h3>
              </div>
              <span className="text-xs font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 px-3 py-1 rounded-full border border-rose-200 dark:border-rose-800">
                {analysis.recent_mistakes.length} Error(s) Analyzed
              </span>
            </div>

            <div className="space-y-4">
              {analysis.recent_mistakes.map((m, idx) => (
                <div
                  key={m.response_id || idx}
                  className="p-5 rounded-2xl bg-gray-50/70 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs font-semibold text-gray-900 dark:text-white leading-relaxed">
                      <strong className="text-rose-500 mr-1.5">Q{idx + 1}:</strong>
                      {m.question_text}
                    </p>
                    {m.response_time_ms && (
                      <span className="shrink-0 text-[10px] font-mono text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">
                        {(m.response_time_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs">
                    <div className="px-3 py-1.5 rounded-xl bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800 font-bold">
                      Your Answer: ✗ [{m.user_answer || "Skipped"}]
                    </div>
                    <div className="px-3 py-1.5 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold">
                      Correct Answer: ✓ [{m.correct_answer}]
                    </div>
                  </div>

                  {m.explanation && (
                    <div className="p-3 rounded-xl bg-white/80 dark:bg-gray-900/60 border border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                      <strong className="text-gray-800 dark:text-gray-200 block mb-1">
                        Worked Syllabus Solution:
                      </strong>
                      {m.explanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upstream Prerequisite Mistakes */}
        {analysis?.ancestor_mistakes && analysis.ancestor_mistakes.length > 0 && (
          <div className="p-6 rounded-3xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                  ✦ Upstream Root Cause Verification
                </span>
                <h3 className="text-lg font-black text-gray-900 dark:text-white mt-0.5">
                  Correlated Mistakes on Prerequisite Ancestors
                </h3>
                <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                  You previously made errors on these prerequisite topics, confirming that foundational gaps directly propagated into your difficulty with {analysis.surface_concept_name}.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {analysis.ancestor_mistakes.map((am, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-2xl bg-white dark:bg-gray-800/80 border border-amber-200 dark:border-amber-800/60 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-800 dark:text-amber-300 text-xs">
                      {am.ancestor_concept_name}
                    </span>
                    <button
                      onClick={() => handleSelectConcept(am.ancestor_concept_id)}
                      className="text-[10px] text-purple-600 dark:text-purple-400 hover:underline font-bold"
                    >
                      Diagnose Node →
                    </button>
                  </div>
                  <p className="text-gray-700 dark:text-gray-300 line-clamp-2 italic">
                    "{am.question_text}"
                  </p>
                  <div className="flex items-center space-x-2 text-[11px]">
                    <span className="text-rose-500 font-bold">Your: [{am.user_answer || "—"}]</span>
                    <span className="text-gray-400">•</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                      Correct: [{am.correct_answer}]
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Phase 4 Cognitive Error Classification */}
        {analysis?.error_classification && (
          <div className="p-6 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                  ✦ Cognitive Error Classification
                </span>
                <h3 className="text-lg font-black text-gray-900 dark:text-white mt-0.5">
                  Diagnosis Grounded in User Evidence
                </h3>
              </div>
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${getErrorTypeBadgeColor(
                  analysis.error_classification.error_type
                )}`}
              >
                {analysis.error_classification.label || analysis.error_classification.error_type}
              </span>
            </div>

            <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
              {analysis.error_classification.explanation}
            </p>

            <div className="flex items-center space-x-4 pt-2 text-[11px] text-gray-400 border-t border-gray-100 dark:border-gray-800">
              <span>
                Evidence Source:{" "}
                <strong className="text-gray-600 dark:text-gray-300 font-mono">
                  {analysis.error_classification.evidence_source || "evaluation_engine"}
                </strong>
              </span>
              <span>
                Diagnostic Confidence:{" "}
                <strong className="text-purple-600 dark:text-purple-400 font-mono">
                  {Math.round((analysis.error_classification.confidence || 0) * 100)}%
                </strong>
              </span>
            </div>
          </div>
        )}

        {/* Phase 5 Weekly Rolling 7-Day Adaptation Snapshot */}
        {weeklyData && weeklyData.latest && (
          <div className="p-6 rounded-3xl bg-gradient-to-br from-indigo-900/20 via-purple-900/10 to-transparent border border-indigo-200/50 dark:border-indigo-800/50 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  ✦ Weekly Adaptation & Refresh Engine (7-Day Rolling Window)
                </span>
                <h3 className="text-lg font-black text-gray-900 dark:text-white mt-0.5">
                  Rolling Adaptation Summary
                </h3>
              </div>
              <button
                onClick={handleManualWeeklyRefresh}
                disabled={refreshingWeekly}
                className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-gray-800 hover:bg-gray-50 border border-indigo-200 dark:border-indigo-700 text-indigo-700 dark:text-indigo-300 shadow-sm disabled:opacity-50"
              >
                <span>{refreshingWeekly ? "Recalculating…" : "⟳ Recalculate Weekly Adaptation"}</span>
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-2xl bg-white/70 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
                <span className="text-[10px] text-gray-400 block uppercase">7-Day Window Range</span>
                <strong className="text-gray-900 dark:text-white text-xs mt-0.5 block truncate">
                  {weeklyData.latest.window_start ? new Date(weeklyData.latest.window_start).toLocaleDateString() : "—"}
                  {" – "}
                  {weeklyData.latest.window_end ? new Date(weeklyData.latest.window_end).toLocaleDateString() : "—"}
                </strong>
              </div>

              <div className="p-3 rounded-2xl bg-white/70 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
                <span className="text-[10px] text-gray-400 block uppercase">Calculated Timestamp</span>
                <strong className="text-gray-900 dark:text-white text-xs mt-0.5 block truncate">
                  {weeklyData.latest.calculated_at ? new Date(weeklyData.latest.calculated_at).toLocaleTimeString() : "—"}
                </strong>
              </div>

              <div className="p-3 rounded-2xl bg-white/70 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
                <span className="text-[10px] text-gray-400 block uppercase">Window Attempts & Acc</span>
                <strong className="text-gray-900 dark:text-white text-xs mt-0.5 block">
                  {weeklyData.latest.total_attempts} drills ({weeklyData.latest.accuracy_pct}%)
                </strong>
              </div>

              <div className="p-3 rounded-2xl bg-white/70 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
                <span className="text-[10px] text-gray-400 block uppercase">WoW Mastery Delta</span>
                <strong
                  className={`text-xs mt-0.5 block font-mono font-bold ${
                    weeklyData.comparison?.wow_mastery_delta >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-500"
                  }`}
                >
                  {weeklyData.comparison?.wow_mastery_delta >= 0 ? "+" : ""}
                  {(weeklyData.comparison?.wow_mastery_delta * 100).toFixed(1)}%
                </strong>
              </div>
            </div>

            {weeklyData.comparison?.remediation_progress_note && (
              <p className="text-xs text-indigo-700 dark:text-indigo-300 italic bg-indigo-50/50 dark:bg-indigo-950/30 p-2.5 rounded-xl border border-indigo-100 dark:border-indigo-900/50">
                {weeklyData.comparison.remediation_progress_note}
              </p>
            )}
          </div>
        )}

        {/* Diagnosed Cognitive Root Causes from 3 Sub-Questions */}
        {analysis?.cognitive_gaps && analysis.cognitive_gaps.length > 0 && (
          <div className="p-6 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                  ✦ Cognitive Process Diagnostic
                </span>
                <h3 className="text-lg font-black text-gray-900 dark:text-white mt-0.5">
                  Diagnosed Cognitive Step Gaps (3 Sub-Question Analysis)
                </h3>
              </div>
              <span className="text-xs text-gray-400 font-medium">
                {analysis.cognitive_gaps.length} Question(s) Diagnosed
              </span>
            </div>

            <div className="space-y-4">
              {analysis.cognitive_gaps.map((item) => {
                const gap = item.cognitive_gap;
                const isFormula = gap.gap_type.includes("Formula");
                const isSetup = gap.gap_type.includes("Application");
                const isAccuracy = gap.gap_type.includes("accuracy");
                const isSpeed = gap.gap_type.includes("speed");

                const badgeColor = isFormula
                  ? "bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 border-rose-200 dark:border-rose-800"
                  : isSetup
                  ? "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 border-amber-200 dark:border-amber-800"
                  : isAccuracy
                  ? "bg-orange-100 text-orange-700 dark:bg-orange-950/50 dark:text-orange-300 border-orange-200 dark:border-orange-800"
                  : isSpeed
                  ? "bg-purple-100 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300 border-purple-200 dark:border-purple-800"
                  : "bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 border-blue-200 dark:border-blue-800";

                return (
                  <div
                    key={item.id}
                    className="p-5 rounded-2xl bg-gray-50/60 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-800 space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h4 className="font-bold text-gray-900 dark:text-white text-sm">
                            {item.topic_name} · {item.concept_name}
                          </h4>
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${badgeColor}`}>
                            {gap.gap_type}
                          </span>
                        </div>
                        {item.main_question_stem && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-1 italic">
                            "{item.main_question_stem}"
                          </p>
                        )}
                      </div>
                      <div className="text-xs font-medium text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40 px-3 py-1.5 rounded-xl border border-purple-200 dark:border-purple-800/50">
                        Task: <strong>{gap.study_task}</strong>
                      </div>
                    </div>

                    {/* 3 Sub-Question Stage Statuses */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
                      {gap.stages.map((stg) => (
                        <div
                          key={stg.stage}
                          className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
                            stg.is_correct && !stg.timed_out
                              ? "bg-emerald-50/70 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/50 text-emerald-800 dark:text-emerald-300"
                              : stg.timed_out
                              ? "bg-purple-50/70 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800/50 text-purple-800 dark:text-purple-300"
                              : "bg-rose-50/70 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800/50 text-rose-800 dark:text-rose-300"
                          }`}
                        >
                          <div>
                            <span className="font-semibold block">{stg.name}</span>
                            <span className="text-[10px] opacity-80">
                              {stg.stage === "calculation" && stg.time_ms
                                ? `${(stg.time_ms / 1000).toFixed(1)}s elapsed`
                                : stg.stage === "calculation"
                                ? "Timed 20s"
                                : "Untimed check"}
                            </span>
                          </div>
                          <span className="font-bold text-sm">
                            {stg.timed_out ? "⏱ >20s" : stg.is_correct ? "✓ Pass" : "✗ Gap"}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* All three failed alert */}
                    {gap.all_three_failed && (
                      <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-xs text-amber-800 dark:text-amber-300 flex items-center space-x-2">
                        <span>⚠️</span>
                        <span>
                          <strong>All 3 stages missed:</strong> Foundational root-cause traced upstream via DAG prerequisites.
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
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
              {analysis?.attribution_state === "no_valid_prerequisites"
                ? "This concept is a verified root node in the curriculum graph with no prior prerequisites."
                : analysis?.attribution_state === "missing_graph_mapping"
                ? "This concept is not yet linked in the curriculum dependency DAG."
                : "No prerequisite weaknesses flagged. Take further practice drills to calibrate prerequisite attribution."}
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

                      {/* Quantitative Readouts and Remediation Action */}
                      <div className="flex flex-wrap items-center sm:justify-end gap-4 text-xs">
                        <div className="text-right">
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Attention α</span>
                          <span className="font-mono font-bold text-purple-600 dark:text-purple-400 text-sm">
                            {(cand.attention_alpha * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Root Score R</span>
                          <span className="font-mono font-bold text-gray-900 dark:text-white text-sm">
                            {cand.root_score.toFixed(3)}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Mastery M_h</span>
                          <span className="font-mono font-bold text-gray-700 dark:text-gray-300 text-sm">
                            {(cand.candidate_mastery * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Error Ev</span>
                          <span className="font-mono font-bold text-rose-500 text-sm">
                            {cand.error_evidence.toFixed(2)}
                          </span>
                        </div>
                        <Link
                          to={`/learning-path?concept_id=${cand.candidate_concept_id}`}
                          className="px-3 py-1.5 rounded-xl text-xs font-bold bg-purple-100 hover:bg-purple-200 dark:bg-purple-950/60 dark:hover:bg-purple-900/80 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800"
                        >
                          Remediate →
                        </Link>
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
