import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { targetApi, profileApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Onboarding() {
  const { refreshProfile } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [track, setTrack] = useState(null); // 'it_career' or 'govt_exam'
  const [targets, setTargets] = useState([]);
  const [selectedTargetId, setSelectedTargetId] = useState(null);

  // Step 3 fields
  const [currentLevel, setCurrentLevel] = useState("Intermediate");
  const [examDate, setExamDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 90);
    return d.toISOString().split("T")[0];
  });
  const [dailyHours, setDailyHours] = useState(2.0);
  const [trialConsent, setTrialConsent] = useState(true);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const fetchTargets = () => {
    setLoading(true);
    setError(null);
    targetApi
      .list()
      .then((data) => {
        setTargets(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        setError("Failed to load available career curricula. Please retry.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTargets();
  }, []);

  const filteredTargets = targets.filter((t) => t.category === track);

  const handleFinishOnboarding = async () => {
    if (!selectedTargetId) {
      setError("Please select a target.");
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      await profileApi.update({
        target_id: selectedTargetId,
        current_level: currentLevel,
        target_exam_date: examDate,
        daily_study_hours: parseFloat(dailyHours),
        trial_consent: trialConsent,
      });

      await refreshProfile();
      navigate("/diagnostic/instructions");
    } catch (err) {
      setError(err.message || "Failed to save onboarding configuration.");
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 py-12">
      <div className="max-w-2xl w-full bg-white dark:bg-gray-900 rounded-3xl shadow-2xl border border-purple-100 dark:border-purple-900/40 p-8 sm:p-10">
        {/* Step Indicator */}
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center space-x-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                  step === s
                    ? "bg-purple-600 text-white shadow-md shadow-purple-500/30"
                    : step > s
                    ? "bg-emerald-500 text-white"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-400"
                }`}
              >
                {step > s ? "✓" : s}
              </div>
            ))}
          </div>
          <span className="text-xs font-semibold text-gray-400">Step {step} of 3</span>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}

        {/* STEP 1: TRACK SELECTION */}
        {step === 1 && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Choose Your Track</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-6">
              Select your primary educational path. Curricula and prerequisite DAGs are tailored to your objective.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => {
                  setTrack("it_career");
                  setStep(2);
                }}
                className="p-6 rounded-2xl border-2 border-gray-200 dark:border-gray-700 hover:border-purple-600 dark:hover:border-purple-500 text-left transition-all hover:shadow-lg group"
              >
                <div className="text-4xl mb-3">💻</div>
                <h3 className="font-bold text-base text-gray-900 dark:text-white group-hover:text-purple-600">
                  IT / Software Engineering
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Machine Learning, Full Stack, Cyber Security, and Generative AI specializations.
                </p>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTrack("govt_exam");
                  setStep(2);
                }}
                className="p-6 rounded-2xl border-2 border-gray-200 dark:border-gray-700 hover:border-purple-600 dark:hover:border-purple-500 text-left transition-all hover:shadow-lg group"
              >
                <div className="text-4xl mb-3">🏛️</div>
                <h3 className="font-bold text-base text-gray-900 dark:text-white group-hover:text-purple-600">
                  Government Competitive Exams
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  UPSC Civil Services, SSC CGL, and Banking examinations with rigorous prerequisite hierarchies.
                </p>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: TARGET SELECTION */}
        {step === 2 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Select Your Specific Target</h2>
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-purple-600 hover:underline"
              >
                ← Change Track
              </button>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Choose the specific role or exam you are preparing for:
            </p>

            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {loading ? (
                <div className="py-12 flex flex-col items-center justify-center space-y-3">
                  <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                    Loading curriculum targets…
                  </span>
                </div>
              ) : filteredTargets.length === 0 ? (
                <div className="p-6 rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 text-center space-y-3 my-4">
                  <div className="text-2xl">📋</div>
                  <h4 className="text-sm font-bold text-gray-800 dark:text-gray-200">
                    No Targets Available Yet
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                    Curricula targets are currently synchronizing from the database. Click below to refresh.
                  </p>
                  <button
                    type="button"
                    onClick={fetchTargets}
                    className="px-4 py-2 text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white rounded-xl shadow-md transition-all inline-flex items-center space-x-1.5"
                  >
                    <span>↻</span>
                    <span>Reload Curricula</span>
                  </button>
                </div>
              ) : (
                filteredTargets.map((t) => {
                  const isSelected = selectedTargetId === t.id;
                  return (
                    <label
                      key={t.id}
                      onClick={() => setSelectedTargetId(t.id)}
                      className={`flex items-start p-4 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? "border-purple-600 bg-purple-50/50 dark:bg-purple-900/20 text-purple-950 dark:text-purple-100 shadow-sm"
                          : "border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600/50 text-gray-800 dark:text-gray-200"
                      }`}
                    >
                      <div
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mr-3 mt-0.5 shrink-0 ${
                          isSelected
                            ? "border-purple-600 bg-purple-600 text-white"
                            : "border-gray-300 dark:border-gray-600"
                        }`}
                      >
                        {isSelected && <span className="text-[10px]">✓</span>}
                      </div>
                      <div className="flex-1">
                        <div className="font-bold text-sm text-gray-900 dark:text-white">{t.name}</div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{t.description}</p>
                        <div className="flex items-center space-x-3 mt-2 text-[11px] text-gray-400">
                          <span>{t.skill_count} Skills</span>
                          <span>•</span>
                          <span>{t.concept_count} Concepts</span>
                          <span>•</span>
                          <span>{t.question_count} Curated Questions</span>
                        </div>
                      </div>
                    </label>
                  );
                })
              )}
            </div>

            <div className="mt-8 flex justify-end">
              <button
                type="button"
                disabled={!selectedTargetId}
                onClick={() => setStep(3)}
                className="py-3 px-6 rounded-xl font-semibold text-sm bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-purple-500/20 transition-all"
              >
                Continue to Step 3 →
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: LEVEL, EXAM DATE, HOURS, AND TRIAL CONSENT */}
        {step === 3 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Configure Study Parameters</h2>
              <button
                type="button"
                onClick={() => setStep(2)}
                className="text-xs text-purple-600 hover:underline"
              >
                ← Back
              </button>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              These inputs calibrate your adaptive remediation priority (Formula 14) and spacing decay schedules:
            </p>

            <div className="space-y-5">
              {/* Current Level */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Current Competency Level
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {["Beginner", "Intermediate", "Advanced"].map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setCurrentLevel(lvl)}
                      className={`py-2.5 px-3 rounded-xl border text-xs font-semibold transition-all ${
                        currentLevel === lvl
                          ? "border-purple-600 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
                          : "border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Exam Date */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Target Exam / Target Completion Date
                </label>
                <input
                  type="date"
                  value={examDate}
                  onChange={(e) => setExamDate(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-[11px] text-gray-400 mt-1">
                  Used by Formula 14 (Urgency = clip(1 - days/H, 0.1, 1)) to rank competing remediation items.
                </p>
              </div>

              {/* Daily Study Hours */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                    Daily Study Commitment
                  </label>
                  <span className="text-xs font-bold text-purple-600">{dailyHours} hours / day</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="10.0"
                  step="0.5"
                  value={dailyHours}
                  onChange={(e) => setDailyHours(e.target.value)}
                  className="w-full accent-purple-600"
                />
              </div>

              {/* Research Trial Consent Checkbox */}
              <div className="p-4 rounded-xl bg-purple-50/50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800">
                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={trialConsent}
                    onChange={(e) => setTrialConsent(e.target.checked)}
                    className="mt-0.5 rounded text-purple-600 focus:ring-purple-500"
                  />
                  <div className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                    <strong>Informed Research Trial Participation</strong>: I consent to anonymized telemetry collection (response times, skip actions, and pre/post test gains) for the RCT-GAT pedagogical study.
                  </div>
                </label>
              </div>
            </div>

            <div className="mt-8 flex justify-end">
              <button
                type="button"
                disabled={submitting}
                onClick={handleFinishOnboarding}
                className="w-full py-3.5 px-6 rounded-xl font-bold text-sm bg-gradient-to-r from-purple-600 via-indigo-600 to-rose-500 hover:from-purple-700 hover:to-rose-600 text-white shadow-xl shadow-purple-500/20 transition-all disabled:opacity-50"
              >
                {submitting ? "Saving Configuration…" : "Proceed to Initial Diagnostic →"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
