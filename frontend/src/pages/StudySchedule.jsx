import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { scheduleApi, weeklyTestApi } from "../api/client";

export default function StudySchedule() {
  const [schedule, setSchedule] = useState([]);
  const [weeklyStatus, setWeeklyStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatingId, setUpdatingId] = useState(null);

  const fetchSchedule = () => {
    setLoading(true);
    Promise.all([
      scheduleApi.get(),
      weeklyTestApi.getStatus().catch(() => null),
    ])
      .then(([schedData, wtData]) => {
        setSchedule(schedData.schedule || []);
        setWeeklyStatus(wtData);
      })
      .catch((err) => setError(err.message || "Failed to load study schedule"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  const toggleComplete = async (item) => {
    setUpdatingId(item.id);
    try {
      const updated = await scheduleApi.update(item.id, {
        completed: !item.completed,
      });
      setSchedule((prev) =>
        prev.map((s) => (s.id === item.id ? { ...s, ...updated } : s))
      );
    } catch (err) {
      alert("Failed to update status: " + err.message);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleReschedule = async (item, days) => {
    setUpdatingId(item.id);
    try {
      const updated = await scheduleApi.update(item.id, {
        reschedule_days: days,
      });
      setSchedule((prev) =>
        prev.map((s) => (s.id === item.id ? { ...s, ...updated } : s))
      );
    } catch (err) {
      alert("Failed to reschedule: " + err.message);
    } finally {
      setUpdatingId(null);
    }
  };

  const completedCount = schedule.filter((s) => s.completed).length;
  const overdueCount = schedule.filter((s) => s.is_overdue).length;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
              Spaced Repetition Study Schedule
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Review dates calibrated dynamically using Ebbinghaus retention decay (F15) and adaptive review intervals (F16).
            </p>
          </div>
        </div>

        {/* Stats Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-sm">
            <span className="text-xs text-gray-400 block font-medium">Scheduled Sessions</span>
            <span className="text-2xl font-black text-gray-900 dark:text-white mt-1">
              {schedule.length}
            </span>
          </div>
          <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-sm">
            <span className="text-xs text-gray-400 block font-medium">Completed</span>
            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
              {completedCount}
            </span>
          </div>
          <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-sm">
            <span className="text-xs text-gray-400 block font-medium">Pending</span>
            <span className="text-2xl font-black text-purple-600 dark:text-purple-400 mt-1">
              {schedule.length - completedCount}
            </span>
          </div>
          <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-rose-200 dark:border-rose-900/40 shadow-sm">
            <span className="text-xs text-rose-600 dark:text-rose-400 block font-medium">
              Overdue
            </span>
            <span className="text-2xl font-black text-rose-600 dark:text-rose-400 mt-1">
              {overdueCount}
            </span>
          </div>
        </div>

        {weeklyStatus?.is_overdue && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
            <div className="flex items-start space-x-3">
              <span className="text-xl shrink-0 mt-0.5">⚠️</span>
              <div>
                <h4 className="text-sm font-bold text-rose-800 dark:text-rose-200">
                  Weekly Progress Test is Overdue
                </h4>
                <p className="text-xs text-rose-600 dark:text-rose-400 mt-0.5">
                  Your Day 7 assessment scheduled for {weeklyStatus.scheduled_date} is overdue. Take the 20-question test now to calibrate your mastery gains and generate your next week's schedule.
                </p>
              </div>
            </div>
            <Link
              to="/weekly-test"
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shrink-0 shadow-md shadow-rose-600/20 self-end sm:self-auto"
            >
              Take Test Now →
            </Link>
          </div>
        )}

        {loading && (
          <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Calculating memory decay schedules…</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm overflow-hidden">
            <div className="p-4 sm:p-6 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
              <h2 className="font-bold text-gray-900 dark:text-white text-base">
                Upcoming Learning &amp; Review Blocks
              </h2>
              <span className="text-xs text-gray-400">
                Formula 16: $\Delta t = \Delta t_0 \cdot \exp(\gamma \cdot m_c)$
              </span>
            </div>

            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {schedule.map((item) => {
                const isWeekly = item.is_weekly_test || item.activity_type === "weekly_test";

                if (isWeekly) {
                  const isLocked = !item.completed && !item.is_overdue && !(weeklyStatus?.is_due || new Date(item.scheduled_date) <= new Date());

                  return (
                    <div
                      key={item.id}
                      className={`p-4 sm:p-6 transition-colors ${
                        item.completed
                          ? "bg-emerald-50/20 dark:bg-emerald-950/10"
                          : item.is_overdue
                          ? "bg-rose-50/30 dark:bg-rose-950/20"
                          : "bg-purple-50/30 dark:bg-purple-950/10"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="flex items-start space-x-3.5">
                          <div className="w-9 h-9 rounded-xl bg-purple-600 text-white flex items-center justify-center font-bold text-base shrink-0 mt-0.5 shadow-md shadow-purple-500/20">
                            📝
                          </div>

                          <div>
                            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                              <h3 className="font-black text-sm text-gray-900 dark:text-white">
                                Weekly Progress Test (20 Qs)
                              </h3>
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                                Day 7 Assessment
                              </span>
                              {item.is_overdue && (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-900">
                                  Overdue
                                </span>
                              )}
                              {item.completed && (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400">
                                  Completed
                                </span>
                              )}
                            </div>

                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              Comprehensive 20-item milestone: weekly priority topics, prerequisite root causes, and spaced reviews. Recalibrates next week's schedule.
                            </p>

                            <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                              <span>📅 Scheduled: {item.scheduled_date}</span>
                              <span>⏱️ 30 mins</span>
                              <span>🎯 20 MCQs</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 self-end sm:self-auto shrink-0">
                          {item.completed ? (
                            <span className="px-3.5 py-1.5 rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 text-xs font-bold">
                              Completed ✓
                            </span>
                          ) : isLocked ? (
                            <button
                              type="button"
                              disabled
                              className="px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 text-xs font-bold cursor-not-allowed"
                              title={`Assessment unlocks on ${item.scheduled_date}`}
                            >
                              Not due yet
                            </button>
                          ) : (
                            <Link
                              to="/weekly-test"
                              className="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white text-xs font-bold shadow-md shadow-purple-500/20 transition-all"
                            >
                              Take Weekly Test →
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={item.id}
                    className={`p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors ${
                      item.completed ? "bg-emerald-50/20 dark:bg-emerald-950/10" : ""
                    }`}
                  >
                    <div className="flex items-start space-x-3.5">
                      <button
                        type="button"
                        disabled={updatingId === item.id}
                        onClick={() => toggleComplete(item)}
                        className={`w-6 h-6 rounded-lg border flex items-center justify-center transition-colors shrink-0 mt-0.5 ${
                          item.completed
                            ? "bg-emerald-500 border-emerald-500 text-white"
                            : "border-gray-300 dark:border-gray-700 hover:border-purple-500"
                        }`}
                      >
                        {item.completed && "✓"}
                      </button>

                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                          <h3
                            className={`font-bold text-sm ${
                              item.completed
                                ? "line-through text-gray-400 dark:text-gray-500"
                                : "text-gray-900 dark:text-white"
                            }`}
                          >
                            {item.concept_name}
                          </h3>
                          {item.subject && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                              {item.subject}
                            </span>
                          )}
                          {item.topic && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                              {item.topic}
                            </span>
                          )}
                          {item.is_overdue && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-900">
                              Overdue
                            </span>
                          )}
                          {item.completed && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400">
                              Completed
                            </span>
                          )}
                        </div>

                        {item.learning_objective && (
                          <p className="text-xs text-gray-600 dark:text-gray-300">
                            <strong>Objective:</strong> {item.learning_objective}
                          </p>
                        )}

                        {item.plan_reason && (
                          <p className="text-[11px] text-purple-600 dark:text-purple-400 italic">
                            💡 {item.plan_reason}
                          </p>
                        )}

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400 pt-1">
                          <span>📅 {item.scheduled_date}</span>
                          <span>⏱️ {item.planned_minutes || item.duration_min || 45} mins</span>
                          <span>🎯 Target: {Math.round((item.mastery_target || 0.8) * 100)}%</span>
                          {item.practice_activity && (
                            <span>📝 {item.practice_activity}</span>
                          )}
                        </div>

                        {item.resource_title && item.resource_url && (
                          <div className="pt-1 flex items-center gap-2 flex-wrap">
                            <span className="text-[11px] text-gray-400">Study Resource:</span>
                            <a
                              href={item.resource_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-purple-600 dark:text-purple-400 hover:underline font-medium inline-flex items-center gap-1"
                            >
                              <span>📖 {item.resource_title}</span>
                              <span className="text-[10px]">↗</span>
                            </a>
                          </div>
                        )}

                        {item.follow_up_assessment && (
                          <div className="text-[11px] text-gray-400 pt-0.5">
                            🔍 Follow-up: <span className="font-medium text-gray-600 dark:text-gray-300">{item.follow_up_assessment}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 self-end sm:self-auto">
                      <button
                        type="button"
                        disabled={updatingId === item.id}
                        onClick={() => handleReschedule(item, 1)}
                        className="px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 text-[11px] font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                        title="Postpone 1 day"
                      >
                        +1 Day
                      </button>
                      <button
                        type="button"
                        disabled={updatingId === item.id}
                        onClick={() => handleReschedule(item, 3)}
                        className="px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 text-[11px] font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                        title="Postpone 3 days"
                      >
                        +3 Days
                      </button>
                    </div>
                  </div>
                );
              })}

              {schedule.length === 0 && (
                <div className="p-12 text-center space-y-4">
                  <div className="w-14 h-14 bg-purple-100 dark:bg-purple-900/30 rounded-2xl flex items-center justify-center text-2xl mx-auto text-purple-600">
                    📅
                  </div>
                  <h3 className="font-bold text-gray-900 dark:text-white text-base">
                    No Scheduled Reviews Yet
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 max-w-md mx-auto leading-relaxed">
                    Complete your 10-question Initial Diagnostic to calibrate your Ebbinghaus memory decay curves and schedule spaced repetition reviews.
                  </p>
                  <Link
                    to="/diagnostic/instructions"
                    className="inline-block px-5 py-2.5 rounded-xl font-bold text-xs bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20 transition-all"
                  >
                    Take Initial Diagnostic →
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
