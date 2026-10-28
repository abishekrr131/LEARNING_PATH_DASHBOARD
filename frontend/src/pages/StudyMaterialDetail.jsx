import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { learningApi } from "../api/client";
import { toOptionList } from "../utils/options";

export default function StudyMaterialDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [resource, setResource] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [revealedSolutions, setRevealedSolutions] = useState({});

  const loadResourceDetail = useCallback(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    learningApi
      .getResourceDetail(id)
      .then((data) => {
        setResource(data);
      })
      .catch((err) => {
        setError(err.message || "Failed to load study material.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  useEffect(() => {
    loadResourceDetail();
  }, [loadResourceDetail]);

  const toggleSolution = (qId) => {
    setRevealedSolutions((prev) => ({
      ...prev,
      [qId]: !prev[qId],
    }));
  };

  const getTypeBadge = (type) => {
    const t = (type || "").toLowerCase();
    if (t === "video") return { icon: "🎬", label: "Video Tutorial", bg: "bg-red-50 text-red-700 dark:bg-red-950/60 dark:text-red-300 border-red-200 dark:border-red-900" };
    if (t === "textbook") return { icon: "📖", label: "Textbook", bg: "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900" };
    if (t === "documentation") return { icon: "📑", label: "Documentation", bg: "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-900" };
    if (t === "interactive") return { icon: "💻", label: "Interactive Guide", bg: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900" };
    if (t === "practice") return { icon: "✍️", label: "Practice Drill", bg: "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-900" };
    return { icon: "📄", label: "Curated Study Notes", bg: "bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-900" };
  };

  return (
    <MainLayout>
      <div className="max-w-5xl mx-auto space-y-6 pb-12">
        {/* Navigation Breadcrumb & Back button */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
            <Link
              to="/resources"
              className="inline-flex items-center space-x-1 font-semibold text-purple-600 dark:text-purple-400 hover:underline"
            >
              <span>← Back to Study Materials</span>
            </Link>
            {resource && (
              <>
                <span>/</span>
                <span className="font-medium text-gray-700 dark:text-gray-300 truncate max-w-[140px]">
                  {resource.target_name}
                </span>
                <span>/</span>
                <span className="truncate max-w-[140px]">{resource.topic_name}</span>
                <span>/</span>
                <span className="text-gray-900 dark:text-white font-semibold truncate max-w-[160px]">
                  {resource.concept_name}
                </span>
              </>
            )}
          </div>
          <Link
            to="/resources"
            className="self-start sm:self-auto px-3.5 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 transition-all shadow-sm"
          >
            ← View All Resources
          </Link>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="p-16 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm">
            <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h3 className="font-bold text-gray-900 dark:text-white">Loading Study Material…</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Fetching curriculum notes, key takeaways, and illustrative worked examples.
            </p>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-2xl border border-rose-200 dark:border-rose-900 shadow-sm space-y-4">
            <div className="text-3xl">⚠️</div>
            <h3 className="font-bold text-gray-900 dark:text-white">Study Material Not Found</h3>
            <p className="text-xs text-rose-600 dark:text-rose-400 max-w-md mx-auto">{error}</p>
            <div className="flex justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={loadResourceDetail}
                className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
              >
                Retry
              </button>
              <Link
                to="/resources"
                className="px-5 py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold transition-all"
              >
                Return to Study Materials
              </Link>
            </div>
          </div>
        )}

        {/* Loaded Content */}
        {!loading && !error && resource && (
          <div className="space-y-6">
            {/* Hero Card */}
            <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4">
              <div className="flex items-center gap-2 flex-wrap">
                {(() => {
                  const badge = getTypeBadge(resource.resource_type);
                  return (
                    <span className={`px-2.5 py-0.5 rounded text-xs font-semibold border ${badge.bg}`}>
                      {badge.icon} {badge.label}
                    </span>
                  );
                })()}
                {resource.is_weak_topic && (
                  <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-900">
                    ⚠️ Weak Topic ({resource.mastery_score}% Mastery)
                  </span>
                )}
                <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                  {resource.target_name}
                </span>
                <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                  ⏱️ {resource.duration_min || 30} mins
                </span>
                <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 capitalize">
                  📊 {resource.difficulty || "Intermediate"}
                </span>
              </div>

              <div>
                <h1 className="text-2xl sm:text-3xl font-black text-gray-900 dark:text-white tracking-tight leading-tight">
                  {resource.title}
                </h1>
                <div className="flex items-center space-x-2 text-sm text-purple-600 dark:text-purple-400 font-semibold mt-1">
                  <span>{resource.skill_name}</span>
                  <span>·</span>
                  <span>{resource.topic_name}</span>
                  <span>·</span>
                  <span className="text-gray-600 dark:text-gray-300 font-bold">{resource.concept_name}</span>
                </div>
              </div>

              {/* Weak Topic Alert banner */}
              {resource.is_weak_topic && (
                <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-800 dark:text-rose-200 leading-relaxed">
                  <strong>Diagnostic Recommendation:</strong> Your current demonstrated mastery in{" "}
                  <span className="font-semibold">{resource.concept_name}</span> is{" "}
                  {resource.mastery_score}%. Reviewing the key syllabus points and worked examples below will help reinforce this concept before your next weekly assessment.
                </div>
              )}

              {/* Source attribution bar */}
              <div className="pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                <div>
                  <strong>Curriculum Provider:</strong> {resource.provider || "Official Academic Curriculum"}
                </div>
                <div>
                  <strong>License:</strong> {resource.license || "Educational Open Access"}
                </div>
              </div>
            </div>

            {/* Core Syllabus Scope & Concepts Breakdown */}
            <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                  <span>📖</span>
                  <span>Curriculum Scope &amp; Key Concepts</span>
                </h2>
                <span className="text-xs text-purple-600 dark:text-purple-400 font-semibold bg-purple-50 dark:bg-purple-950/40 px-2.5 py-1 rounded-lg">
                  Syllabus Breakdown
                </span>
              </div>

              {resource.description && (
                <div className="p-4 bg-slate-50 dark:bg-gray-800/60 rounded-xl border border-slate-200 dark:border-gray-700/60 text-sm text-gray-700 dark:text-gray-200 leading-relaxed">
                  <p className="font-medium text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                    Syllabus Overview
                  </p>
                  <p>{resource.description}</p>
                </div>
              )}

              {/* Key points tags */}
              {resource.key_points && resource.key_points.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2.5">
                    Essential Syllabus Components
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {resource.key_points.map((point, idx) => (
                      <div
                        key={idx}
                        className="flex items-start space-x-2 p-3 bg-purple-50/50 dark:bg-purple-950/20 rounded-xl border border-purple-100 dark:border-purple-900/40"
                      >
                        <span className="text-purple-600 dark:text-purple-400 font-bold text-xs mt-0.5">
                          ✓
                        </span>
                        <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
                          {point}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Study Recommendations */}
              <div className="p-4 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/40 space-y-2">
                <h4 className="text-xs font-bold text-indigo-900 dark:text-indigo-200 uppercase tracking-wider">
                  💡 High-Yield Study Tips
                </h4>
                <ul className="text-xs text-indigo-800 dark:text-indigo-300 space-y-1.5 list-disc list-inside leading-relaxed">
                  <li>
                    Focus on foundational terminology and historical/structural relationships before attempting complex drills.
                  </li>
                  <li>
                    Analyze how this concept connects to previous prerequisite topics and exam pyqs (previous year questions).
                  </li>
                  <li>
                    Verify each answer step thoroughly using the worked examples below.
                  </li>
                </ul>
              </div>
            </div>

            {/* Worked Examples / Exam Practice Questions */}
            {resource.worked_examples && resource.worked_examples.length > 0 && (
              <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                      <span>✍️</span>
                      <span>Worked Examples &amp; Illustrative Questions</span>
                    </h2>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Targeted question walkthroughs with verified explanations from the question bank.
                    </p>
                  </div>
                  <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300">
                    {resource.worked_examples.length} Examples
                  </span>
                </div>

                <div className="space-y-4">
                  {resource.worked_examples.map((ex, index) => {
                    const isRevealed = Boolean(revealedSolutions[ex.id]);
                    const optionsList = toOptionList(ex.options);

                    return (
                      <div
                        key={ex.id || index}
                        className="p-5 rounded-2xl border border-gray-200 dark:border-gray-800 bg-slate-50/50 dark:bg-gray-800/40 space-y-3"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-600 text-white">
                              Example {index + 1}
                            </span>
                            {ex.exam_year && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                                Exam: {ex.exam_year}
                              </span>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => toggleSolution(ex.id)}
                            className="px-3 py-1 text-xs font-semibold rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600 text-purple-600 dark:text-purple-400 transition-colors shadow-sm"
                          >
                            {isRevealed ? "Hide Explanation" : "Reveal Answer & Explanation"}
                          </button>
                        </div>

                        <p className="text-sm font-semibold text-gray-900 dark:text-white leading-snug">
                          {ex.question_text}
                        </p>

                        {/* Options */}
                        {optionsList.length > 0 && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                            {optionsList.map((opt) => {
                              const isCorrect = isRevealed && opt.key === ex.correct_answer;
                              return (
                                <div
                                  key={opt.key}
                                  className={`p-2.5 rounded-xl border text-xs flex items-center space-x-2 transition-all ${
                                    isCorrect
                                      ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 font-bold"
                                      : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300"
                                  }`}
                                >
                                  <span
                                    className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold ${
                                      isCorrect
                                        ? "bg-emerald-600 text-white"
                                        : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                                    }`}
                                  >
                                    {opt.key}
                                  </span>
                                  <span className="flex-1">{opt.text}</span>
                                  {isCorrect && <span>✓ Correct</span>}
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {/* Explanation reveal */}
                        {isRevealed && (
                          <div className="mt-3 p-3.5 rounded-xl bg-purple-50/70 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900 text-xs text-purple-950 dark:text-purple-200 space-y-1 animate-fadeIn">
                            <span className="font-bold text-[11px] text-purple-700 dark:text-purple-300 uppercase tracking-wider block">
                              Detailed Solution Walkthrough (Correct: Option {ex.correct_answer})
                            </span>
                            <p className="leading-relaxed">{ex.explanation}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Prerequisites & Curriculum Connections */}
            {((resource.prerequisites && resource.prerequisites.length > 0) ||
              (resource.unlocked_concepts && resource.unlocked_concepts.length > 0)) && (
              <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4">
                <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                  <span>🔗</span>
                  <span>Curriculum Graph &amp; Prerequisites</span>
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {resource.prerequisites && resource.prerequisites.length > 0 && (
                    <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-800/40 border border-slate-200 dark:border-gray-700/60">
                      <h3 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2">
                        Prerequisites to Review First
                      </h3>
                      <div className="space-y-1.5">
                        {resource.prerequisites.map((p) => (
                          <Link
                            key={p.id}
                            to={`/resources/${p.id}`}
                            className="block p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs text-purple-600 dark:text-purple-400 hover:border-purple-400 transition-colors font-medium"
                          >
                            ← {p.name} ({p.topic})
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}

                  {resource.unlocked_concepts && resource.unlocked_concepts.length > 0 && (
                    <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-800/40 border border-slate-200 dark:border-gray-700/60">
                      <h3 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2">
                        Concepts Unlocked Next
                      </h3>
                      <div className="space-y-1.5">
                        {resource.unlocked_concepts.map((u) => (
                          <Link
                            key={u.id}
                            to={`/resources/${u.id}`}
                            className="block p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs text-gray-700 dark:text-gray-300 hover:border-purple-400 transition-colors font-medium"
                          >
                            → {u.name} ({u.topic})
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Authoritative External References */}
            {resource.external_references && resource.external_references.length > 0 && (
              <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                      <span>🌐</span>
                      <span>Authoritative External References &amp; Portals</span>
                    </h2>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Official repositories, national educational archives, and video lectures.
                    </p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                    Verified Sources
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {resource.external_references.map((ref, idx) => (
                    <a
                      key={idx}
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-800/80 hover:border-purple-400 dark:hover:border-purple-500 transition-all flex flex-col justify-between group shadow-sm"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400 uppercase tracking-wider">
                            {ref.source}
                          </span>
                          <span className="text-gray-400 group-hover:text-purple-600 transition-colors text-xs">
                            ↗
                          </span>
                        </div>
                        <h4 className="text-xs font-bold text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors line-clamp-2">
                          {ref.title}
                        </h4>
                      </div>
                      <span className="mt-2 text-[10px] text-gray-400">
                        Open verified source in new tab
                      </span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Bottom Actions Bar */}
            <div className="p-6 bg-gradient-to-r from-purple-50 via-white to-indigo-50 dark:from-purple-950/20 dark:via-gray-900 dark:to-indigo-950/20 rounded-2xl border border-purple-100 dark:border-purple-900/40 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-gray-900 dark:text-white text-sm">
                  Ready to test your knowledge on {resource.concept_name}?
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Launch adaptive practice drills calibrated to your skill level.
                </p>
              </div>

              <div className="flex items-center space-x-3 w-full sm:w-auto">
                <Link
                  to="/resources"
                  className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 transition-all text-center flex-1 sm:flex-initial"
                >
                  All Materials
                </Link>
                <Link
                  to="/practice"
                  className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-500/20 transition-all text-center flex-1 sm:flex-initial"
                >
                  Practice Drills →
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
