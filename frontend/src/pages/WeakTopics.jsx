import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { analyticsApi } from "../api/client";
import MainLayout from "../layouts/MainLayout";

export default function WeakTopics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterBand, setFilterBand] = useState("all");

  const [mistakeData, setMistakeData] = useState(null);
  const [loadingMistakes, setLoadingMistakes] = useState(true);
  const [expandedSessionId, setExpandedSessionId] = useState(null);
  const [viewFilter, setViewFilter] = useState("mistakes");

  useEffect(() => {
    analyticsApi
      .getGaps()
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || "Failed to load skill gap analytics");
        setData({ gaps: [] });
      })
      .finally(() => setLoading(false));

    analyticsApi
      .getMistakeHistory()
      .then((res) => {
        setMistakeData(res);
      })
      .catch((err) => {
        console.error("Failed to load mistake history:", err);
        setMistakeData({ sessions: [], total_sessions: 0, total_mistakes: 0 });
      })
      .finally(() => setLoadingMistakes(false));
  }, []);

  const gaps = data?.gaps || [];
  const subjectRecs = data?.subject_recommendations || [];
  const week1Plan = data?.week_1_plan || [];
  const diagPerf = data?.latest_diagnostic || null;
  const summary = data?.summary || {};

  const filtered = gaps.filter((g) => {
    if (filterBand === "all") return true;
    if (filterBand === "unassessed") return g.status === "unassessed";
    return g.band === filterBand;
  });

  const hasDiagnosticData = Boolean(data?.diagnostic_completed || (data?.total_attempts && data.total_attempts > 0));

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">
              Skill Gap & Weak Topics Analysis
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Evidence-based competency diagnosis via Formula 12 gap scores, syllabus progression rules, and adaptive Week 1 study tasks for {data?.target_name || "your target career"}.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <span className="text-gray-400">Filter Band:</span>
            {["all", "weak", "moderate", "strong", "unassessed"].map((b) => (
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

        {/* Diagnostic Performance & Readiness Overview */}
        {diagPerf && (
          <div className="p-6 rounded-3xl bg-gradient-to-r from-purple-900/90 via-indigo-900/80 to-purple-950 border border-purple-500/30 text-white shadow-xl shadow-purple-900/10">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <span className="inline-block px-3 py-1 rounded-full text-[11px] font-bold bg-purple-500/30 border border-purple-400/30 text-purple-200 mb-2">
                  ✓ Initial Diagnostic Test Evaluated
                </span>
                <h2 className="text-xl font-black">
                  Calibrated Performance Baseline
                </h2>
                <p className="text-xs text-purple-200 mt-1 max-w-xl leading-relaxed">
                  Raw question accuracy is separated from syllabus coverage. Mastery thresholds (&ge;80%) require verified assessment evidence before advancing.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div className="bg-white/10 backdrop-blur-md p-3.5 rounded-2xl border border-white/10">
                  <div className="text-2xl font-black">{diagPerf.accuracy_pct}%</div>
                  <div className="text-[10px] text-purple-200 font-semibold uppercase mt-0.5">Raw Accuracy</div>
                  <div className="text-[9px] text-purple-300 font-mono mt-0.5">{diagPerf.correct_count}/{diagPerf.total_questions} Questions</div>
                </div>

                <div className="bg-white/10 backdrop-blur-md p-3.5 rounded-2xl border border-white/10">
                  <div className="text-2xl font-black">{diagPerf.topic_coverage_readiness}%</div>
                  <div className="text-[10px] text-purple-200 font-semibold uppercase mt-0.5">Topic Coverage</div>
                  <div className="text-[9px] text-purple-300 font-mono mt-0.5">{diagPerf.distinct_topics_demonstrated}/{diagPerf.total_syllabus_topics} Topics</div>
                </div>

                <div className="bg-white/10 backdrop-blur-md p-3.5 rounded-2xl border border-white/10">
                  <div className="text-2xl font-black text-rose-300">{summary.weak_count || 0}</div>
                  <div className="text-[10px] text-purple-200 font-semibold uppercase mt-0.5">Weak Priorities</div>
                  <div className="text-[9px] text-rose-300 font-mono mt-0.5">Pausing advance</div>
                </div>

                <div className="bg-white/10 backdrop-blur-md p-3.5 rounded-2xl border border-white/10">
                  <div className="text-2xl font-black text-emerald-300">{summary.strengths_count || 0}</div>
                  <div className="text-[10px] text-purple-200 font-semibold uppercase mt-0.5">Demonstrated</div>
                  <div className="text-[9px] text-emerald-300 font-mono mt-0.5">Mastery unlocked</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Assessment Mistake History Section */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-lg font-black text-gray-900 dark:text-white flex items-center gap-2">
                <span>🔍</span> Assessment Mistake History & Question Review
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Review specific questions answered incorrectly or skipped in your Initial Diagnostic, Week 1, and Week 2 assessments with complete explanations.
              </p>
            </div>
            {mistakeData?.sessions?.length > 0 && (
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-gray-400 text-[11px]">Filter View:</span>
                <button
                  type="button"
                  onClick={() => setViewFilter("mistakes")}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                    viewFilter === "mistakes"
                      ? "bg-rose-600 text-white shadow-md shadow-rose-500/20"
                      : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400"
                  }`}
                >
                  Mistakes Only ({mistakeData.total_mistakes})
                </button>
                <button
                  type="button"
                  onClick={() => setViewFilter("all")}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                    viewFilter === "all"
                      ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                      : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400"
                  }`}
                >
                  All Questions
                </button>
              </div>
            )}
          </div>

          {loadingMistakes ? (
            <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-3xl border border-gray-100 dark:border-gray-800 text-xs text-gray-400">
              Loading mistake history…
            </div>
          ) : !mistakeData || mistakeData.sessions.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-3xl border border-dashed border-gray-300 dark:border-gray-800 space-y-3">
              <div className="text-3xl">📋</div>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                No Assessment Mistakes Recorded Yet
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                Once you complete your Initial Diagnostic or Weekly Tests, any incorrect or skipped questions will be documented here with detailed explanations.
              </p>
              <Link
                to="/diagnostic/instructions"
                className="inline-block px-4 py-2 rounded-xl font-bold text-xs bg-purple-600 hover:bg-purple-700 text-white shadow-md transition-all"
              >
                Take Initial Diagnostic →
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Session Accordion Cards */}
              {mistakeData.sessions.map((session) => {
                const isExpanded = expandedSessionId === session.assessment_id;
                const itemsToShow = viewFilter === "mistakes" ? session.mistakes : session.all_items;
                const dateStr = session.completed_at
                  ? new Date(session.completed_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })
                  : "";

                return (
                  <div
                    key={session.assessment_id}
                    className="bg-white dark:bg-gray-900 rounded-3xl border border-purple-100 dark:border-purple-900/40 shadow-sm overflow-hidden transition-all"
                  >
                    {/* Session Header Card (Clickable to toggle) */}
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => setExpandedSessionId(isExpanded ? null : session.assessment_id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          setExpandedSessionId(isExpanded ? null : session.assessment_id);
                        }
                      }}
                      className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-purple-50/30 dark:hover:bg-purple-950/20 transition-all select-none"
                    >
                      <div className="flex items-center space-x-3.5">
                        <div
                          className={`w-10 h-10 rounded-2xl flex items-center justify-center font-bold text-lg ${
                            session.mistakes_count > 0
                              ? "bg-rose-100 dark:bg-rose-950/60 text-rose-600 border border-rose-200 dark:border-rose-800"
                              : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 border border-emerald-200 dark:border-emerald-800"
                          }`}
                        >
                          {session.mistakes_count > 0 ? "⚠️" : "✓"}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="text-base font-black text-gray-900 dark:text-white">
                              {session.title}
                            </h3>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300">
                              {session.short_label}
                            </span>
                          </div>
                          <div className="flex items-center space-x-3 text-xs text-gray-400 mt-0.5">
                            {dateStr && <span>Completed {dateStr}</span>}
                            <span>•</span>
                            <span>
                              Score: <strong className="text-gray-700 dark:text-gray-300">{session.score_pct}%</strong> ({session.correct_count}/{session.total_questions} correct)
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3 self-end sm:self-auto">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-black ${
                            session.mistakes_count > 0
                              ? "bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
                              : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                          }`}
                        >
                          {session.mistakes_count > 0
                            ? `${session.mistakes_count} Mistake${session.mistakes_count > 1 ? "s" : ""}`
                            : "100% Accurate"}
                        </span>
                        <span className="text-xs font-bold text-purple-600 dark:text-purple-400">
                          {isExpanded ? "Collapse ▲" : "View Mistakes ▼"}
                        </span>
                      </div>
                    </div>

                    {/* Expanded Content (Questions and Explanations) */}
                    {isExpanded && (
                      <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-950/30 space-y-6">
                        {itemsToShow.length === 0 ? (
                          <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-2xl border border-emerald-200 dark:border-emerald-900/40">
                            <span className="text-3xl block mb-2">🎉</span>
                            <h4 className="text-sm font-bold text-emerald-700 dark:text-emerald-300">
                              No Mistakes in this Assessment!
                            </h4>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              Every question in this session was answered correctly ({session.total_questions}/{session.total_questions}).
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            <div className="flex items-center justify-between text-xs text-gray-500">
                              <span>
                                Showing <strong>{itemsToShow.length}</strong> {viewFilter === "mistakes" ? "mistakes" : "questions"} in {session.title}:
                              </span>
                            </div>

                            {itemsToShow.map((item, qIdx) => {
                              const isWrong = !item.is_correct && !item.skipped;
                              const isSkipped = item.skipped;
                              const isCorrect = item.is_correct;

                              return (
                                <div
                                  key={item.question_id || qIdx}
                                  className={`p-5 rounded-2xl border transition-all ${
                                    isWrong
                                      ? "bg-white dark:bg-gray-900 border-rose-200 dark:border-rose-900/60 shadow-sm"
                                      : isSkipped
                                      ? "bg-white dark:bg-gray-900 border-amber-200 dark:border-amber-900/60 shadow-sm"
                                      : "bg-white dark:bg-gray-900 border-emerald-200 dark:border-emerald-900/60 shadow-sm"
                                  }`}
                                >
                                  {/* Question Header */}
                                  <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                                    <div className="flex items-center space-x-2">
                                      <span
                                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-black ${
                                          isWrong
                                            ? "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                                            : isSkipped
                                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                                            : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                                        }`}
                                      >
                                        {isWrong ? "✗ Incorrect" : isSkipped ? "⊘ Skipped" : "✓ Correct"}
                                      </span>
                                      <span className="text-xs font-bold text-gray-400">
                                        Question #{qIdx + 1}
                                      </span>
                                    </div>

                                    <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                                      <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 font-medium">
                                        {item.skill_name}
                                      </span>
                                      <span className="px-2 py-0.5 rounded bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 font-semibold border border-purple-200 dark:border-purple-800">
                                        {item.topic_name}
                                      </span>
                                      <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800">
                                        {item.concept_name}
                                      </span>
                                    </div>
                                  </div>

                                  {/* Question Stem */}
                                  <p className="text-sm font-semibold text-gray-900 dark:text-white leading-relaxed mb-4">
                                    {item.question_text}
                                  </p>

                                  {/* MCQ Options Display */}
                                  {item.options && Object.keys(item.options).length > 0 && (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mb-4">
                                      {Object.entries(item.options).map(([optKey, optVal]) => {
                                        const wasSelected = item.selected_answer === optKey;
                                        const isTheCorrect = item.correct_answer === optKey;

                                        return (
                                          <div
                                            key={optKey}
                                            className={`p-3 rounded-xl border text-xs flex items-start space-x-2.5 transition-all ${
                                              isTheCorrect
                                                ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-400 dark:border-emerald-600 text-emerald-950 dark:text-emerald-200 font-semibold shadow-sm"
                                                : wasSelected && !isTheCorrect
                                                ? "bg-rose-50 dark:bg-rose-950/30 border-rose-400 dark:border-rose-600 text-rose-950 dark:text-rose-200 line-through opacity-90 shadow-sm"
                                                : "bg-gray-50/70 dark:bg-gray-800/40 border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-300"
                                            }`}
                                          >
                                            <span
                                              className={`w-6 h-6 rounded-lg flex items-center justify-center font-bold text-[11px] shrink-0 ${
                                                isTheCorrect
                                                  ? "bg-emerald-600 text-white"
                                                  : wasSelected
                                                  ? "bg-rose-600 text-white"
                                                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                                              }`}
                                            >
                                              {optKey}
                                            </span>
                                            <div className="flex-1">
                                              <span>{optVal}</span>
                                              {isTheCorrect && (
                                                <span className="block text-[10px] text-emerald-600 dark:text-emerald-400 font-bold mt-0.5">
                                                  ✓ Correct Answer
                                                </span>
                                              )}
                                              {wasSelected && !isTheCorrect && (
                                                <span className="block text-[10px] text-rose-600 dark:text-rose-400 font-bold mt-0.5">
                                                  ✗ Your Choice
                                                </span>
                                              )}
                                            </div>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}

                                  {/* Answer Comparison Summary Callout */}
                                  <div className="p-3.5 rounded-xl bg-gray-100/70 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 flex flex-wrap items-center justify-between gap-3 text-xs mb-3">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-gray-500 text-[11px]">Your Answer:</span>
                                      <span
                                        className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                                          item.is_correct
                                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                                            : item.skipped
                                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                                            : "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                                        }`}
                                      >
                                        {item.skipped ? "Skipped" : `[${item.selected_answer}] ${item.selected_text}`}
                                      </span>
                                    </div>

                                    <div className="flex items-center space-x-2">
                                      <span className="text-gray-500 text-[11px]">Correct Answer:</span>
                                      <span className="font-bold px-2 py-0.5 rounded text-[11px] bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                                        [{item.correct_answer}] {item.correct_text}
                                      </span>
                                    </div>

                                    {item.response_time_ms > 0 && (
                                      <div className="text-[11px] text-gray-400 font-mono">
                                        Time: {(item.response_time_ms / 1000).toFixed(1)}s
                                      </div>
                                    )}
                                  </div>

                                  {/* Detailed Explanation Box */}
                                  {item.explanation && (
                                    <div className="p-3.5 rounded-xl bg-purple-50/60 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/50 text-xs">
                                      <div className="font-bold text-purple-700 dark:text-purple-300 flex items-center gap-1.5 mb-1">
                                        <span>💡</span> Detailed Explanation:
                                      </div>
                                      <p className="text-gray-700 dark:text-gray-300 text-[12px] leading-relaxed">
                                        {item.explanation}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Subject-by-Subject Progression Rules Card */}
        {subjectRecs.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-black text-gray-900 dark:text-white flex items-center gap-2">
                <span>🧭</span> Subject Progression & Next Recommended Topics
              </h2>
              <span className="text-xs text-gray-400">
                Independent syllabus advancement rules applied per subject
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {subjectRecs.map((sr, idx) => {
                const isMastered = sr.status_badge === "mastered";
                const isWeak = sr.status_badge === "weak";
                const isUnassessed = sr.status_badge === "unassessed";

                return (
                  <div
                    key={idx}
                    className={`p-5 rounded-2xl border flex flex-col justify-between transition-all shadow-sm ${
                      isMastered
                        ? "bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800"
                        : isWeak
                        ? "bg-rose-50/50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800"
                        : "bg-gray-50/60 dark:bg-gray-900/40 border-gray-200 dark:border-gray-800"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-xs font-bold text-gray-900 dark:text-white truncate">
                          {sr.subject}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-500">
                          Weight: {Math.round(sr.weight * 100)}%
                        </span>
                      </div>

                      <div className="mb-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            isMastered
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300"
                              : isWeak
                              ? "bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300"
                              : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                          }`}
                        >
                          {sr.status}
                        </span>
                      </div>

                      <div className="text-xs text-gray-600 dark:text-gray-300 mb-2">
                        <span className="text-gray-400 block text-[10px] uppercase font-bold">Assessed Topic:</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {sr.assessed_topic || "Not yet tested in diagnostic"}
                        </span>{" "}
                        {sr.demonstrated_accuracy && (
                          <span className="font-mono text-xs text-purple-600 dark:text-purple-400 font-bold">
                            ({sr.demonstrated_accuracy})
                          </span>
                        )}
                      </div>

                      <div className="p-3 rounded-xl bg-white dark:bg-gray-800/80 border border-gray-100 dark:border-gray-700/60 mb-3">
                        <span className="text-[10px] uppercase font-bold text-purple-600 dark:text-purple-400 block mb-0.5">
                          {isMastered ? "Next Eligible Topic:" : "Remediation Topic:"}
                        </span>
                        <div className="font-black text-xs text-gray-900 dark:text-white">
                          {sr.recommended_topic}
                        </div>
                      </div>

                      <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">
                        {sr.reason}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800/60 flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-gray-700 dark:text-gray-300">
                        {sr.action}
                      </span>
                      <span>{isMastered ? "🔓" : isWeak ? "🛑" : "📋"}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* First Week Study Plan Generated From Diagnostic */}
        {week1Plan.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-black text-gray-900 dark:text-white flex items-center gap-2">
                  <span>📅</span> Generated Week 1 Study Plan
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Persisted 7-day adaptive progression schedule prioritizing diagnosed root causes and unlocked topics.
                </p>
              </div>
              <Link
                to="/schedule"
                className="text-xs font-bold text-purple-600 dark:text-purple-400 hover:underline"
              >
                Open Full Schedule →
              </Link>
            </div>

            <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-purple-100 dark:border-purple-900/40 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-xs">
                  <thead className="bg-gray-50/70 dark:bg-gray-800/50">
                    <tr>
                      <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Day / Date</th>
                      <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Subject</th>
                      <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Topic</th>
                      <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Learning Objective</th>
                      <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Verified Study Material</th>
                      <th className="px-5 py-3.5 text-center font-semibold text-gray-600 dark:text-gray-300">Target</th>
                      <th className="px-5 py-3.5 text-center font-semibold text-gray-600 dark:text-gray-300">Duration</th>
                      <th className="px-5 py-3.5 text-right font-semibold text-gray-600 dark:text-gray-300">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {week1Plan.map((item, idx) => {
                      const isTest = item.activity_type === "weekly_test";
                      const dynamicDate = (() => {
                        const d = new Date();
                        d.setDate(d.getDate() + idx);
                        const iso = d.toISOString().split("T")[0];
                        // If item.scheduled_date exists and is today or future, use it; otherwise dynamicDate
                        if (item.scheduled_date) {
                          const todayStr = new Date().toISOString().split("T")[0];
                          if (item.scheduled_date >= todayStr) return item.scheduled_date;
                        }
                        return iso;
                      })();
                      return (
                        <tr key={item.id || idx} className="hover:bg-purple-50/20 dark:hover:bg-purple-900/10">
                          <td className="px-5 py-4 whitespace-nowrap">
                            <span className="font-bold text-gray-900 dark:text-white block">
                              Day {idx + 1}
                            </span>
                            <span className="text-[10px] text-gray-400 font-mono">
                              {dynamicDate}
                            </span>
                          </td>
                          <td className="px-5 py-4 font-semibold text-purple-700 dark:text-purple-300">
                            {item.subject}
                          </td>
                          <td className="px-5 py-4">
                            <div className="font-bold text-gray-900 dark:text-white">
                              {item.topic_name}
                            </div>
                            <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                              {item.plan_reason}
                            </span>
                          </td>
                          <td className="px-5 py-4 max-w-xs text-gray-600 dark:text-gray-300 text-[11px] leading-relaxed">
                            {item.learning_objective}
                          </td>
                          <td className="px-5 py-4 max-w-xs">
                            <a
                              href={item.resource_url}
                              target="_blank"
                              rel="noreferrer"
                              className="font-bold text-purple-600 dark:text-purple-400 hover:underline block text-[11px] truncate"
                            >
                              📖 {item.resource_title} ↗
                            </a>
                            <span className="text-[10px] text-gray-400 block mt-0.5">
                              {item.practice_activity}
                            </span>
                          </td>
                          <td className="px-5 py-4 text-center font-mono font-bold text-gray-700 dark:text-gray-300">
                            {Math.round(item.mastery_target * 100)}%
                          </td>
                          <td className="px-5 py-4 text-center font-mono text-gray-500 dark:text-gray-400">
                            {item.duration_min}m
                          </td>
                          <td className="px-5 py-4 text-right">
                            {item.completed ? (
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                                ✓ Completed
                              </span>
                            ) : isTest ? (
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300">
                                Milestone Test
                              </span>
                            ) : (
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                                Pending
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

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

        {/* Decomposed Table of Gaps */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-purple-100 dark:border-purple-900/40 overflow-hidden">
          <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <div>
              <h2 className="text-base font-black text-gray-900 dark:text-white">
                All Curriculum Concepts & Gap Matrix
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Showing {filtered.length} of {gaps.length} total concepts
              </p>
            </div>
          </div>

          {loading ? (
            <div className="py-12 text-center text-xs text-gray-400">Computing gap matrix…</div>
          ) : !hasDiagnosticData && gaps.every((g) => g.status === "unassessed") ? (
            <div className="py-16 px-6 text-center space-y-4">
              <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/30 rounded-2xl flex items-center justify-center text-2xl mx-auto text-purple-600">
                📉
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                No Concept Gaps Assessed Yet
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 max-w-md mx-auto leading-relaxed">
                Empirical accuracy, response time ratios, and Formula 12 gap scores are computed only after you take assessments.
              </p>
              <Link
                to="/diagnostic/instructions"
                className="inline-block px-5 py-2.5 rounded-xl font-bold text-xs bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20 transition-all"
              >
                Take Initial Diagnostic →
              </Link>
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-400">No concepts match the selected filter.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-xs">
                <thead className="bg-gray-50/70 dark:bg-gray-800/50">
                  <tr>
                    <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Concept</th>
                    <th className="px-5 py-3.5 text-left font-semibold text-gray-600 dark:text-gray-300">Topic</th>
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
                  {filtered.map((g) => {
                    const isUnassessed = g.status === "unassessed";
                    return (
                      <tr key={g.concept_id} className="hover:bg-purple-50/20 dark:hover:bg-purple-900/10">
                        <td className="px-5 py-4 font-bold text-gray-900 dark:text-white">{g.concept_name}</td>
                        <td className="px-5 py-4 text-gray-600 dark:text-gray-300 font-medium">{g.topic_name || "--"}</td>
                        <td className="px-5 py-4 text-gray-500 dark:text-gray-400">{g.skill_name}</td>
                        <td className="px-5 py-4 text-center font-mono">
                          {isUnassessed ? "--" : `${(g.accuracy * 100).toFixed(0)}%`}
                        </td>
                        <td className="px-5 py-4 text-center font-mono">
                          {isUnassessed ? "--" : `${g.time_ratio.toFixed(2)}x`}
                        </td>
                        <td className="px-5 py-4 text-center font-mono">
                          {isUnassessed ? "--" : `${(g.skip_rate * 100).toFixed(0)}%`}
                        </td>
                        <td className="px-5 py-4 text-center font-mono">
                          {isUnassessed ? "--" : g.historical_mastery.toFixed(2)}
                        </td>
                        <td className="px-5 py-4 text-center font-mono font-bold text-purple-600 dark:text-purple-400">
                          {isUnassessed ? "--" : g.gap_score.toFixed(3)}
                        </td>
                        <td className="px-5 py-4 text-center">
                          {isUnassessed ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                              Not assessed yet
                            </span>
                          ) : g.band ? (
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
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                              Calibrating (N=1)
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-center font-mono font-bold text-indigo-600 dark:text-indigo-400">
                          {isUnassessed ? "--" : g.priority.toFixed(4)}
                        </td>
                        <td className="px-5 py-4 text-right">
                          {isUnassessed ? (
                            <span className="text-xs text-gray-400 italic">Unassessed</span>
                          ) : (
                            <Link
                              to={`/root-cause?concept_id=${g.concept_id}`}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:bg-purple-600 hover:text-white transition-all"
                            >
                              Trace Cause →
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
