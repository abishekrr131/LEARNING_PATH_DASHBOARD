import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { assessmentApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import AssessmentRunner from "../components/AssessmentRunner";

export default function FollowUpRunner() {
  const { profile } = useAuth();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const targetId = profile?.target_id || 1;
    assessmentApi
      .start({
        type: "followup",
        target_id: targetId,
      })
      .then((data) => {
        setAssessment(data);
      })
      .catch((err) => {
        setError(err.message || "Failed to initialize follow-up assessment.");
      })
      .finally(() => setLoading(false));
  }, [profile]);

  const handleSubmitted = (submitOut) => {
    navigate(`/result/${submitOut.assessment_id}`, {
      state: {
        result: {
          ...submitOut,
          is_followup: true,
          summary: "Post-remediation assessment completed. Your updated mastery scores have been incorporated into your learning path.",
        },
      },
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4" />
        <h3 className="font-bold text-gray-900 dark:text-white">Generating Follow-Up Post-Assessment…</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Sampling approved items across completed remediation topics to evaluate retention and effect size.
        </p>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="p-6 max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-rose-200 dark:border-rose-900">
          <div className="text-3xl mb-2">⚠️</div>
          <h3 className="font-bold text-gray-900 dark:text-white">Unable to Start Follow-Up</h3>
          <p className="text-xs text-rose-600 dark:text-rose-400 mt-2 mb-4">{error}</p>
          <button
            onClick={() => navigate("/dashboard")}
            className="px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-semibold"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 py-12 px-4 sm:px-6">
      <div className="max-w-2xl mx-auto mb-6 p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 text-xs text-emerald-800 dark:text-emerald-200">
        <strong>Research Trial Follow-Up Assessment:</strong> This 10-question evaluation measures knowledge acquisition since your initial diagnostic and validates whether completed prerequisite study has successfully resolved upstream gaps.
      </div>

      <AssessmentRunner
        assessmentId={assessment.assessment_id}
        items={assessment.items}
        onSubmitted={handleSubmitted}
        title="Follow-Up Post-Assessment"
      />
    </div>
  );
}
