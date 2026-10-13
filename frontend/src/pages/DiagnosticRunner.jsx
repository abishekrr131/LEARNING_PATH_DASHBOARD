import React, { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { assessmentApi, diagnosticApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import AssessmentRunner from "../components/AssessmentRunner";

export default function DiagnosticRunner() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [assessment, setAssessment] = useState(location.state?.assessment || null);
  const [loading, setLoading] = useState(!location.state?.assessment);
  const [error, setError] = useState(null);

  const loadAssessment = useCallback(() => {
    setLoading(true);
    setError(null);
    const targetId = profile?.target_id || 1;

    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(
        () => reject(new Error("Diagnostic generation timed out after 90 seconds. Please retry.")),
        90000
      )
    );

    Promise.race([diagnosticApi.start(targetId), timeoutPromise])
      .then((data) => {
        setAssessment(data);
      })
      .catch((err) => {
        if (err?.response?.status === 429 || String(err?.message || "").includes("429") || String(err?.message || "").toLowerCase().includes("busy")) {
          setError("AI is busy, retry in about 1 minute");
          return;
        }
        return assessmentApi.start({
          type: "initial",
          target_id: targetId,
        }).then(setAssessment);
      })
      .catch((err) => {
        if (err?.response?.status === 429 || String(err?.message || "").includes("429") || String(err?.message || "").toLowerCase().includes("busy")) {
          setError("AI is busy, retry in about 1 minute");
        } else {
          setError(err.message || "Failed to initialize diagnostic session.");
        }
      })
      .finally(() => setLoading(false));
  }, [profile?.target_id]);

  useEffect(() => {
    if (!assessment) {
      loadAssessment();
    }
  }, [assessment, loadAssessment]);

  const handleSubmitted = (submitOut) => {
    navigate(`/result/${submitOut.assessment_id}`, { state: { result: submitOut } });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mb-4" />
        <h3 className="font-bold text-gray-900 dark:text-white">Generating your questions with AI. This can take 30-60 seconds.</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-sm">
          Stratifying items across curriculum skills proportional to exam weights.
        </p>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="p-6 max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-rose-200 dark:border-rose-900">
          <div className="text-3xl mb-2">⚠️</div>
          <h3 className="font-bold text-gray-900 dark:text-white">Unable to Start Diagnostic</h3>
          <p className="text-xs text-rose-600 dark:text-rose-400 mt-2 mb-4">{error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={loadAssessment}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold transition-all shadow-md"
            >
              Retry
            </button>
            <button
              onClick={() => navigate("/dashboard")}
              className="px-4 py-2 bg-gray-150 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold"
            >
              Return to Dashboard
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
          diagnosticApi
            .submit(assessment.assessment_id, responses)
            .catch(() => assessmentApi.submit(assessment.assessment_id, responses))
        }
        title="Initial Diagnostic Assessment"
      />
    </div>
  );
}
