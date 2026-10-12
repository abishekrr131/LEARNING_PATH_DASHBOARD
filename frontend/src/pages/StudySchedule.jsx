import React, { useState, useEffect } from "react";
import MainLayout from "../layouts/MainLayout";
import { scheduleApi } from "../api/client";

export default function StudySchedule() {
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatingId, setUpdatingId] = useState(null);

  const fetchSchedule = () => {
    setLoading(true);
    scheduleApi
      .get()
      .then((data) => {
        setSchedule(data.schedule || []);
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
              {schedule.map((item) => (
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

                    <div>
                      <div className="flex items-center space-x-2">
                        <h3
                          className={`font-bold text-sm ${
                            item.completed
                              ? "line-through text-gray-400 dark:text-gray-500"
                              : "text-gray-900 dark:text-white"
                          }`}
                        >
                          {item.concept_name}
                        </h3>
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

                      <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                        <span>📅 {item.scheduled_date}</span>
                        <span>⏱️ {item.planned_minutes} mins</span>
                        <span>ID #{item.concept_id}</span>
                      </div>
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
              ))}

              {schedule.length === 0 && (
                <div className="p-8 text-center text-gray-500 text-sm">
                  No scheduled study sessions found. Complete a diagnostic to generate your adaptive timetable.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
