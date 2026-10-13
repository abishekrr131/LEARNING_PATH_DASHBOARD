import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { weeklyTestApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import AssessmentRunner from "../components/AssessmentRunner";

export default function WeeklyTestRunner() {
  const { profile } = useAuth();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [testStatus, setTestStatus] = useState(null);

  const loadWeeklyTest = useCallback((forceUnlock = false) => {
    setLoading(true);
    setError(null);
    const targetId = profile?.target_id || 1;

    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(
        () => reject(new Error("Weekly test generation timed out after 90 seconds. Please retry.")),
        90000
      )
    );

    Promise.race([weeklyTestApi.start(targetId, forceUnlock), timeoutPromise])
      .then((data) => {
        setAssessment(data);
      })
      .catch((err) => {
        if (err?.response?.status === 429 || String(err?.message || "").includes("429") || String(err?.message || "").toLowerCase().includes("busy")) {
          setError("AI is busy, retry in about 1 minute");
        } else {
          setError(err.message || "Failed to initialize weekly test session.");
        }
      })
      .finally(() => setLoading(false));
  }, [profile?.target_id]);

  useEffect(() => {
    weeklyTestApi
      .getStatus()
      .then((st) => {
        setTestStatus(st);
        if (st.is_due || st.is_overdue || st.status === "completed") {
          loadWeeklyTest(false);
        } else {
          // If locked, check if dev mode allows unlocking
          setLoading(false);
        }
      })
      .catch(() => {
        loadWeeklyTest(true);
      });
  }, [profile, loadWeeklyTest]);

  const handleSubmitted = (submitOut) => {
    navigate(`/weekly-test/result/${submitOut.assessment_id}`, { state: { result: submitOut } });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4" />
        <h3 className="font-bold text-gray-900 dark:text-white">Generating your questions with AI. This can take 30-60 seconds.</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-sm">
          Selecting priority curriculum topics (~50%), prerequisite root causes (~25%), and spaced reviews (~25%) with zero repeated questions.
        </p>
      </div>
    );
  }

  if (testStatus && !testStatus.is_due && !testStatus.is_overdue && !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="p-8 max-w-md bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-purple-100 dark:border-purple-900/40">
          <div className="w-14 h-14 bg-purple-100 dark:bg-purple-900/40 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 text-purple-600 dark:text-purple-300">
            🔒
          </div>
          <h3 className="font-black text-xl text-gray-900 dark:text-white">Weekly Test Not Due Yet</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 mb-6 leading-relaxed">
            Your 20-question Weekly Test is scheduled for <strong>{testStatus.scheduled_date || "Day 7"}</strong>.
            Complete your daily topic reviews to prepare for the test.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => loadWeeklyTest(true)}
              className="py-2.5 px-4 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold transition-all"
            >
              Take Early (Practice Mode)
            </button>
            <button
              onClick={() => navigate("/schedule")}
              className="py-2.5 px-4 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-bold transition-all"
            >
              View Schedule
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="p-6 max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-rose-200 dark:border-rose-900">
          <div className="text-3xl mb-2">⚠️</div>
          <h3 className="font-bold text-gray-900 dark:text-white">Unable to Start Weekly Test</h3>
          <p className="text-xs text-rose-600 dark:text-rose-400 mt-2 mb-4">{error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => loadWeeklyTest(true)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold transition-all"
            >
              Retry
            </button>
            <button
              onClick={() => navigate("/schedule")}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold"
            >
              Return to Schedule
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 py-12 px-4 sm:px-6">
      <AssessmentRunner
        assessmentId={assessment.assessment_id}
        items={assessment.items}
        onSubmitted={handleSubmitted}
        onSubmit={(responses) =>
          weeklyTestApi.submit(assessment.assessment_id, responses)
        }
        title="Weekly Progress Test (20 Questions)"
      />
    </div>
  );
}
