import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { assessmentApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import AssessmentRunner from "../components/AssessmentRunner";

export default function VerificationRunner() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const conceptIdParam = searchParams.get("concept_id");

  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const targetId = profile?.target_id || 1;
    assessmentApi
      .start({
        type: "verification",
        target_id: targetId,
      })
      .then((data) => {
        setAssessment(data);
      })
      .catch((err) => {
        setError(err.message || "Failed to initialize verification probes.");
      })
      .finally(() => setLoading(false));
  }, [profile, conceptIdParam]);

  const handleSubmitted = (submitOut) => {
    navigate(`/root-cause${conceptIdParam ? `?concept_id=${conceptIdParam}` : ""}`, {
      state: { verified: true, result: submitOut },
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8">
        <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4" />
        <h3 className="font-bold text-gray-900 dark:text-white">Assembling Verification Probes…</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Sampling 2–3 items targeting suspected root-cause DAG ancestors with ε-random mix.
        </p>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="p-6 max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-rose-200 dark:border-rose-900">
          <div className="text-3xl mb-2">⚠️</div>
          <h3 className="font-bold text-gray-900 dark:text-white">Unable to Start Verification</h3>
          <p className="text-xs text-rose-600 dark:text-rose-400 mt-2 mb-4">{error}</p>
          <button
            onClick={() => navigate("/root-cause")}
            className="px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-semibold"
          >
            Return to Root Cause Screen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 py-12 px-4 sm:px-6">
      <div className="max-w-2xl mx-auto mb-6 p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 text-xs text-amber-800 dark:text-amber-200">
        <strong>Root Cause Verification Mode:</strong> You are taking targeted probes specifically chosen to confirm whether foundational prerequisites are the source of diagnosed errors.
      </div>

      <AssessmentRunner
        assessmentId={assessment.assessment_id}
        items={assessment.items}
        onSubmitted={handleSubmitted}
        title="Root-Cause Verification Probes"
      />
    </div>
  );
}
