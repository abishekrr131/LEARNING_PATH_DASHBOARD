import React, { useState } from "react";
import { useLocation, useNavigate, useParams, Link } from "react-router-dom";

export default function WeeklyTestResult() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const result = location.state?.result || null;

  if (!result) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <h3 className="font-bold text-gray-900 dark:text-white">Weekly Test Completed</h3>
        <p className="text-xs text-gray-500 mt-2 mb-4">Your results have calibrated next week's schedule.</p>
        <Link to="/schedule" className="px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-semibold">
          View Study Schedule →
        </Link>
      </div>
    );
  }

  const improved = result.improved_topics || [];
  const stillWeak = result.still_weak_topics || [];
  const delta = result.readiness_delta || 0;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 py-12 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Main Card */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-indigo-100 dark:border-indigo-900/40 p-8 sm:p-10">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-600 text-white rounded-2xl flex items-center justify-center text-3xl mx-auto mb-3 shadow-lg shadow-indigo-500/20">
              📊
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
              Weekly Progress Evaluation · Session #{id}
            </span>
            <h2 className="text-3xl font-black text-gray-900 dark:text-white mt-1">
              Week-over-Week Diagnostic Calibration
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Your 20-item test results have recalibrated your topic priorities and generated Next Week's curriculum.
            </p>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <div className="p-4 rounded-2xl bg-purple-50/60 dark:bg-purple-950/30 border border-purple-100 dark:border-purple-800 text-center">
              <span className="text-xs text-gray-500 dark:text-gray-400">Test Score</span>
              <div className="text-2xl font-black text-purple-600 dark:text-purple-400 mt-1">
                {result.score}%
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-800 text-center">
              <span className="text-xs text-gray-500 dark:text-gray-400">Previous Readiness</span>
              <div className="text-2xl font-black text-gray-700 dark:text-gray-300 mt-1">
                {result.previous_readiness}%
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800 text-center">
              <span className="text-xs text-gray-500 dark:text-gray-400">Current Readiness</span>
              <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
                {result.current_readiness}%
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-teal-50/60 dark:bg-teal-950/30 border border-teal-100 dark:border-teal-800 text-center">
              <span className="text-xs text-gray-500 dark:text-gray-400">Readiness Delta</span>
              <div className="text-2xl font-black text-teal-600 dark:text-teal-400 mt-1">
                {delta >= 0 ? `+${delta}%` : `${delta}%`}
              </div>
            </div>
          </div>

          {/* Improved Topics */}
          {improved.length > 0 && (
            <div className="mb-8">
              <h3 className="font-bold text-sm text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <span>📈</span> Demonstrated Mastery Gains (Week-over-Week)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {improved.map((t, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl bg-emerald-50/40 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 flex items-center justify-between"
                  >
                    <div>
                      <span className="text-xs font-bold text-gray-800 dark:text-gray-200 block">
                        {t.topic_name}
                      </span>
                      <span className="text-[11px] text-gray-400">
                        {t.old_mastery}% → <strong>{t.new_mastery}%</strong>
                      </span>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-black bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                      +{t.delta}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Still-Weak Topics Carried Forward */}
          {stillWeak.length > 0 && (
            <div className="mb-8">
              <h3 className="font-bold text-sm text-rose-600 dark:text-rose-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <span>⚠️</span> Still-Weak Topics (Carried Forward into Next Week)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {stillWeak.map((wt, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl bg-rose-50/40 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 flex items-center justify-between"
                  >
                    <div>
                      <span className="text-xs font-bold text-gray-800 dark:text-gray-200 block">
                        {wt.topic_name}
                      </span>
                      <span className="text-[11px] text-gray-400">
                        Current Mastery: {wt.mastery}%
                      </span>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold uppercase bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300">
                      {wt.band}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-gray-100 dark:border-gray-800">
            <Link
              to="/schedule"
              className="py-3.5 px-6 rounded-xl font-bold text-xs bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white shadow-lg shadow-indigo-500/20 text-center transition-all"
            >
              📅 View Next Week's Study Plan →
            </Link>
            <Link
              to="/dashboard"
              className="py-3.5 px-6 rounded-xl font-bold text-xs border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 text-center transition-all"
            >
              Return to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
