import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { analyticsApi, learningApi, scheduleApi, diagnosticApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import MainLayout from "../layouts/MainLayout";

export default function Dashboard() {
  const { profile } = useAuth();
  const [readiness, setReadiness] = useState(null);
  const [gaps, setGaps] = useState([]);
  const [nextSchedule, setNextSchedule] = useState(null);
  const [pathSummary, setPathSummary] = useState(null);
  const [diagnosticStatus, setDiagnosticStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      analyticsApi.getReadiness().catch(() => null),
      analyticsApi.getGaps().catch(() => ({ gaps: [] })),
      scheduleApi.get().catch(() => ({ schedule: [] })),
      learningApi.getPath().catch(() => null),
      diagnosticApi.getStatus().catch(() => null),
    ]).then(([readinessRes, gapsRes, scheduleRes, pathRes, diagRes]) => {
      setReadiness(readinessRes);
      setGaps(gapsRes?.gaps || []);
      const pendingItems = (scheduleRes?.schedule || []).filter((s) => !s.completed);
      setNextSchedule(pendingItems[0] || null);
      setPathSummary(pathRes);
      setDiagnosticStatus(diagRes);
      setLoading(false);
    });
  }, []);

  const topWeak = (gaps || [])
    .filter((g) => g.status !== "unassessed" && g.priority != null && g.gap_score != null)
    .slice(0, 3);

  if (loading) {
    return (
      <MainLayout>
        <div className="flex flex-col items-center justify-center p-20 text-center">
          <div className="w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mb-4" />
          <h3 className="font-bold text-gray-900 dark:text-white">Loading your dashboard…</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Retrieving competency state and syllabus progress.</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Top Hero Banner */}
        <div className="p-8 rounded-3xl bg-gradient-to-r from-purple-700 via-indigo-700 to-rose-600 text-white shadow-xl shadow-purple-500/10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-xl">
            <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-white/20 backdrop-blur-md mb-3">
              ✦ Target: {profile?.target_name || "Curriculum Track"}
            </div>
            <h1 className="text-3xl font-black tracking-tight leading-tight">
              Welcome back, {profile?.name?.split(" ")[0] || "Learner"}!
            </h1>
            <p className="text-sm text-purple-100 mt-2 leading-relaxed">
              Your adaptive competency model is updated in real-time. Target exam:{" "}
              <strong>{profile?.target_exam_date || "Upcoming"}</strong> (Planning Horizon active).
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/special-test"
              className="px-5 py-3 rounded-xl font-bold text-xs bg-rose-500 hover:bg-rose-600 text-white shadow-lg shadow-rose-500/25 transition-all transform hover:-translate-y-0.5"
            >
              ⚡ Launch Special Test (30s Timed)
            </Link>
            <Link
              to="/assessments"
              className="px-5 py-3 rounded-xl font-bold text-xs bg-white text-purple-900 hover:bg-purple-50 shadow-md transition-all"
            >
              Assessments Hub →
            </Link>
          </div>
        </div>

        {/* 3-Column Metrics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 1. Readiness Score Card (F17) */}
          <div className="p-6 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl shadow-purple-500/5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                  Exam Readiness (F17)
                </span>
                <span className="text-[10px] italic text-gray-400">
                  {readiness?.label || "Provisional estimate"}
                </span>
              </div>

              <div className="flex items-baseline space-x-2">
                <span className="text-4xl font-black text-gray-900 dark:text-white">
                  {readiness?.readiness_percentage != null ? `${readiness.readiness_percentage}%` : "0%"}
                </span>
                <span className="text-xs text-gray-400">
                  / Threshold {Math.round((readiness?.readiness_threshold || 0.70) * 100)}%
                </span>
              </div>

              <div className="w-full bg-gray-100 dark:bg-gray-800 h-2.5 rounded-full overflow-hidden my-4">
                <div
                  className="bg-gradient-to-r from-purple-500 to-indigo-600 h-full rounded-full transition-all duration-700"
                  style={{ width: `${readiness?.readiness_percentage || 0}%` }}
                />
              </div>

              {!readiness?.is_assessed && !diagnosticStatus?.is_completed && (
                <div className="mb-4 p-3 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-100 dark:border-purple-900/40 text-xs">
                  <div className="font-bold text-purple-700 dark:text-purple-300 mb-1">Take the Initial Diagnostic</div>
                  <p className="text-gray-500 dark:text-gray-400 text-[11px] mb-2 leading-relaxed">
                    Calibrate your knowledge baseline across syllabus topics with a 10-question assessment.
                  </p>
                  <Link
                    to="/diagnostic/instructions"
                    className="inline-block w-full py-2 px-3 rounded-lg text-center font-bold text-xs bg-purple-600 hover:bg-purple-700 text-white shadow-sm transition-all"
                  >
                    Start Diagnostic Assessment →
                  </Link>
                </div>
              )}

              {diagnosticStatus?.is_completed && (
                <div className="mb-4 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-900/40 text-xs">
                  <div className="flex items-center justify-between font-bold text-emerald-700 dark:text-emerald-300 mb-1">
                    <span>Initial Diagnostic Completed ✓</span>
                    <span className="font-mono text-[11px]">{diagnosticStatus.score != null ? `${Math.round(diagnosticStatus.score)}%` : ""}</span>
                  </div>
                  <p className="text-gray-500 dark:text-gray-400 text-[11px] mb-2 leading-relaxed">
                    Baseline established across target skills. Adaptive schedule & root causes active.
                  </p>
                  <Link
                    to={`/result/${diagnosticStatus.assessment_id}`}
                    className="inline-block w-full py-2 px-3 rounded-lg text-center font-bold text-xs bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all"
                  >
                    Review Diagnostic Results →
                  </Link>
                </div>
              )}

              {/* Skill weights breakdown */}
              <div className="space-y-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
                {readiness?.skill_components?.map((sk) => (
                  <div key={sk.skill_id} className="flex justify-between items-center text-xs">
                    <span className="text-gray-500 dark:text-gray-400 truncate max-w-[150px]">{sk.skill_name}</span>
                    <span className="font-mono font-bold text-gray-700 dark:text-gray-300">
                      {sk.skill_percentage != null ? `${sk.skill_percentage}%` : "0%"} · {sk.progress_text || `${sk.demonstrated_topics || 0} of ${sk.total_topics || 0} demonstrated`}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {readiness?.readiness_percentage != null && (
              <Link
                to="/progress"
                className="block text-center text-xs font-bold text-purple-600 dark:text-purple-400 mt-4 hover:underline"
              >
                Full Readiness Decomposition →
              </Link>
            )}
          </div>

          {/* 2. Path Position Card */}
          <div className="p-6 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl shadow-purple-500/5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  Learning Path State
                </span>
                <span className="text-xs font-mono text-gray-400">DAG Synchronized</span>
              </div>

              {readiness?.is_assessed ? (
                <>
                  <div className="text-2xl font-black text-gray-900 dark:text-white">
                    {pathSummary ? `${pathSummary.completed_count} / ${pathSummary.total_nodes} Nodes` : "--"}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-4 leading-relaxed">
                    {pathSummary?.remediations_active > 0 ? (
                      <span className="text-rose-500 font-semibold">
                        ⚠️ {pathSummary.remediations_active} dynamic prerequisite remediation(s) inserted.
                      </span>
                    ) : (
                      "Curriculum sequence follows strict topological ordering."
                    )}
                  </p>
                </>
              ) : (
                <div className="py-2 space-y-2 mb-4">
                  <div className="text-2xl font-black text-gray-900 dark:text-white">
                    Not assessed yet
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                    Curriculum nodes will calibrate topologically based on your initial diagnostic gaps.
                  </p>
                </div>
              )}
            </div>

            <Link
              to="/learning-path"
              className="w-full py-3 px-4 rounded-xl font-bold text-xs bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-center transition-all"
            >
              View Topological Learning Path →
            </Link>
          </div>

          {/* 3. Next Review Session (F15 / F16 Decay) */}
          <div className="p-6 rounded-3xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl shadow-purple-500/5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-rose-500">
                  Next Scheduled Review (F16)
                </span>
                <span className="text-xs font-mono text-gray-400">Decay Curve</span>
              </div>

              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {nextSchedule ? nextSchedule.concept_name : "All current topics up to date"}
              </div>

              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-4">
                {nextSchedule
                  ? `Scheduled: ${nextSchedule.scheduled_date} · Planned duration: ${nextSchedule.planned_minutes} min`
                  : "No pending Ebbinghaus review dates currently due."}
              </p>
            </div>

            <Link
              to="/schedule"
              className="w-full py-3 px-4 rounded-xl font-bold text-xs bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/60 text-center transition-all"
            >
              Open Study Schedule & Calendar →
            </Link>
          </div>
        </div>

        {/* Priority Remediation Queue (F12 & F14) */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-purple-100 dark:border-purple-900/40 p-6 sm:p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                Priority Remediation Queue (Formula 14 Adaptive Ranking)
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Competency gaps weighted by exam urgency, skill weight, and DAG distance.
              </p>
            </div>
            <Link to="/weak-topics" className="text-xs font-bold text-purple-600 dark:text-purple-400 hover:underline">
              View All Gaps →
            </Link>
          </div>

          {topWeak.length === 0 ? (
            <div className="text-center py-8 text-xs text-gray-400">
              No severe gaps flagged. Take a diagnostic assessment to calibrate your baseline.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topWeak.map((g) => (
                <div
                  key={g.concept_id}
                  className="p-5 rounded-2xl border border-purple-100 dark:border-purple-900/40 bg-purple-50/20 dark:bg-purple-950/20 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                        {g.skill_name}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400">
                        Rank #{g.priority != null ? g.priority.toFixed(3) : "--"}
                      </span>
                    </div>

                    <h3 className="font-bold text-sm text-gray-900 dark:text-white mb-2">{g.concept_name}</h3>

                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 dark:text-gray-400 mb-4">
                      <div>Accuracy: <strong>{g.accuracy != null ? `${(g.accuracy * 100).toFixed(0)}%` : "--"}</strong></div>
                      <div>Gap: <strong>{g.gap_score != null ? g.gap_score.toFixed(3) : "--"}</strong></div>
                    </div>
                  </div>

                  <Link
                    to={`/root-cause?concept_id=${g.concept_id}`}
                    className="w-full py-2.5 px-3 rounded-xl font-bold text-xs bg-purple-600 hover:bg-purple-700 text-white text-center shadow-md shadow-purple-500/10 transition-all"
                  >
                    Trace Prerequisite Root Cause →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
