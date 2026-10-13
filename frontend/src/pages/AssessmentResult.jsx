import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams, Link } from "react-router-dom";
import { learningApi, analyticsApi } from "../api/client";

export default function AssessmentResult() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [result, setResult] = useState(location.state?.result || null);
  const [roadmap, setRoadmap] = useState(location.state?.result?.roadmap || []);
  const [readiness, setReadiness] = useState(null);

  useEffect(() => {
    if (!result?.roadmap || result.roadmap.length === 0) {
      learningApi.getPath().then((p) => {
        if (p?.nodes) setRoadmap(p.nodes);
      }).catch(() => {});
    }
    analyticsApi.getReadiness().then(setReadiness).catch(() => {});
  }, [result]);

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

  const weakTopics = result.weak_topics || (result.per_concept?.filter((c) => c.band === "weak" || c.band === "moderate")) || [];
  const skillBreakdown = result.skill_breakdown || readiness?.skill_components || [];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 py-12 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Main Result Card */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-purple-100 dark:border-purple-900/40 p-8 sm:p-10">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/40 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-3 shadow-md shadow-purple-500/10">
              🎯
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
              Assessment Completed · Session #{id}
            </span>
            <h2 className="text-3xl font-black text-gray-900 dark:text-white mt-1">Diagnostic Evaluation Results</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Competency baseline calibrated and topological remediation roadmap synthesized.
            </p>
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
                {result.correct_count} / {result.total_questions || 10}
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/30 border border-amber-100 dark:border-amber-800 text-center">
              <span className="text-xs text-gray-500 dark:text-gray-400">Skips</span>
              <div className="text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">
                {result.skip_count || 0}
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-800 text-center">
              <span className="text-xs text-gray-500 dark:text-gray-400">Coverage Readiness</span>
              <div className="text-2xl font-black text-indigo-600 dark:text-indigo-400 mt-1">
                {result.topic_coverage_readiness_pct != null
                  ? `${result.topic_coverage_readiness_pct}%`
                  : result.readiness_percentage != null
                  ? `${result.readiness_percentage}%`
                  : (readiness?.readiness_percentage ? `${readiness.readiness_percentage}%` : "--")}
              </div>
              {result.learning_stage && (
                <span className="text-[10px] text-purple-600 dark:text-purple-400 font-bold block mt-0.5">
                  {result.learning_stage}
                </span>
              )}
            </div>
          </div>

          {/* Diagnostic Question-by-Topic Performance & Actions */}
          {result.question_results && result.question_results.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-sm text-gray-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                  <span>📊</span> Diagnostic Performance by Topic &amp; Adaptive Actions
                </h3>
                <span className="text-xs text-purple-600 dark:text-purple-400 font-semibold">
                  Accuracy: {result.question_accuracy_pct != null ? `${result.question_accuracy_pct}%` : `${result.score}%`}
                </span>
              </div>
              <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-gray-800">
                <table className="w-full text-left text-xs text-gray-700 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-800/60 text-gray-400 font-semibold border-b border-gray-200 dark:border-gray-800">
                    <tr>
                      <th className="py-2.5 px-3">#</th>
                      <th className="py-2.5 px-3">Subject &amp; Topic</th>
                      <th className="py-2.5 px-3">Your Answer</th>
                      <th className="py-2.5 px-3">Correct</th>
                      <th className="py-2.5 px-3">Result</th>
                      <th className="py-2.5 px-3">Adaptive Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800/60 bg-white dark:bg-gray-900">
                    {result.question_results.map((qr, idx) => (
                      <tr key={idx} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                        <td className="py-2.5 px-3 font-mono font-bold text-gray-400">{idx + 1}</td>
                        <td className="py-2.5 px-3">
                          <span className="font-bold text-gray-900 dark:text-white block">{qr.topic_name}</span>
                          <span className="text-[10px] text-gray-400">{qr.skill_name}</span>
                        </td>
                        <td className="py-2.5 px-3 font-mono font-semibold">
                          {qr.skipped ? (
                            <span className="text-amber-500 italic">Skipped</span>
                          ) : (
                            <span className={qr.is_correct ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}>
                              Option {qr.learner_answer || "--"}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-gray-700 dark:text-gray-300">
                          Option {qr.correct_answer}
                        </td>
                        <td className="py-2.5 px-3">
                          {qr.is_correct ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400">
                              ✓ Correct (Mastered)
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400">
                              ✗ Weak / Gap
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          {qr.is_correct ? (
                            <span className="text-[11px] text-emerald-700 dark:text-emerald-300 font-medium">
                              🚀 Unlocked next syllabus topic for Week 1
                            </span>
                          ) : (
                            <span className="text-[11px] text-rose-700 dark:text-rose-300 font-medium">
                              ⚠️ Assigned concept revision &amp; practice set
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Per-Skill Breakdown */}
          {skillBreakdown.length > 0 && (
            <div className="mb-8">
              <h3 className="font-bold text-sm text-gray-900 dark:text-white uppercase tracking-wider mb-3">
                Per-Skill Syllabus Breakdown
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {skillBreakdown.map((sk, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl bg-gray-50 dark:bg-gray-800/60 border border-gray-200/60 dark:border-gray-700/60 flex items-center justify-between"
                  >
                    <div>
                      <span className="text-xs font-bold text-gray-800 dark:text-gray-200 block">
                        {sk.skill_name}
                      </span>
                      <span className="text-[11px] text-gray-400">Exam Weight: {sk.weight}</span>
                    </div>
                    <div className="text-right">
                      <span className="font-mono font-bold text-sm text-purple-600 dark:text-purple-400">
                        {sk.accuracy != null ? `${sk.accuracy}%` : (sk.mean_mastery != null ? `${Math.round(sk.mean_mastery * 100)}%` : "--")}
                      </span>
                      <span className="text-[10px] text-gray-400 block">Mastery Level</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Weak Topics Section */}
          {weakTopics.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-sm text-rose-600 dark:text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                  <span>⚠️</span> Identified Weak Topics &amp; Concept Gaps
                </h3>
                <span className="text-xs text-gray-400 font-mono">Formula 12 Scored</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {weakTopics.map((wt, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex justify-between items-start">
                        <h4 className="font-bold text-xs text-gray-900 dark:text-white">
                          {wt.concept_name}
                        </h4>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400">
                          {wt.band}
                        </span>
                      </div>
                      <div className="flex gap-4 mt-2 text-xs text-gray-500">
                        <span>Gap: <strong className="font-mono">{wt.gap_score}</strong></span>
                        {wt.accuracy != null && <span>Accuracy: <strong className="font-mono">{(wt.accuracy * 100).toFixed(0)}%</strong></span>}
                      </div>
                    </div>
                    <Link
                      to={`/root-cause?concept_id=${wt.concept_id}`}
                      className="mt-3 text-xs font-bold text-purple-600 dark:text-purple-400 hover:underline inline-flex items-center"
                    >
                      Inspect Root-Cause Ancestors →
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Generated Topological Roadmap */}
          {roadmap.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-sm text-gray-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                  <span>🗺️</span> Generated Remediation Roadmap
                </h3>
                <span className="text-xs text-gray-400 font-mono">Topologically Sorted</span>
              </div>
              <div className="bg-purple-50/30 dark:bg-purple-950/10 rounded-2xl p-4 border border-purple-100 dark:border-purple-900/40 divide-y divide-purple-100 dark:divide-purple-900/30">
                {roadmap.slice(0, 5).map((node, stepIdx) => (
                  <div key={node.concept_id || stepIdx} className="py-2.5 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-3">
                      <span className="w-6 h-6 rounded-full bg-purple-600 text-white font-bold flex items-center justify-center text-[10px]">
                        {stepIdx + 1}
                      </span>
                      <span className="font-bold text-gray-800 dark:text-gray-200">
                        {node.concept_name}
                      </span>
                      {node.is_remediation && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400">
                          Prerequisite Remediation
                        </span>
                      )}
                    </div>
                    <span className="text-gray-400 font-mono text-[11px]">
                      Mastery: {Math.round((node.mastery || 0.5) * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
            <Link
              to="/schedule"
              className="py-3 px-3 rounded-xl font-bold text-xs bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white shadow-md text-center transition-all"
            >
              📅 Week 1 Plan
            </Link>
            <Link
              to="/learning-path"
              className="py-3 px-3 rounded-xl font-bold text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md text-center transition-all"
            >
              🗺️ Career Ready Map
            </Link>
            <Link
              to="/resources"
              className="py-3 px-3 rounded-xl font-bold text-xs bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white shadow-md text-center transition-all"
            >
              📖 Study Materials
            </Link>
            <Link
              to="/dashboard"
              className="py-3 px-3 rounded-xl font-bold text-xs border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 text-center transition-all"
            >
              Return Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
