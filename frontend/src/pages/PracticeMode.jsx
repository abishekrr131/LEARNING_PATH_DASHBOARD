import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { assessmentApi, aiApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function PracticeMode() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const conceptIdParam = searchParams.get("concept_id");

  const [assessment, setAssessment] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [stats, setStats] = useState({ correct: 0, total: 0 });

  // High precision timer per question
  const startTimeRef = useRef(0);
  const elapsedRef = useRef(0);
  const isHiddenRef = useRef(false);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        elapsedRef.current += performance.now() - startTimeRef.current;
        isHiddenRef.current = true;
      } else {
        startTimeRef.current = performance.now();
        isHiddenRef.current = false;
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  useEffect(() => {
    setLoading(true);
    assessmentApi
      .start({
        type: "practice",
        target_id: profile?.target_id || 1,
      })
      .then((data) => {
        setAssessment(data);
        setCurrentIndex(0);
        setSelectedOption(null);
        setRevealed(false);
        requestAnimationFrame(() => {
          startTimeRef.current = performance.now();
          elapsedRef.current = 0;
        });
      })
      .catch((err) => {
        alert("Failed to initialize practice: " + err.message);
      })
      .finally(() => setLoading(false));
  }, [profile, conceptIdParam]);

  const currentItem = assessment?.items?.[currentIndex];

  const handleSelectOption = (idx) => {
    if (revealed) return;
    setSelectedOption(idx);
  };

  const handleCheckAnswer = () => {
    if (selectedOption === null) return;
    const isCorrect = selectedOption === currentItem.correct_option;
    setRevealed(true);
    setStats((prev) => ({
      correct: prev.correct + (isCorrect ? 1 : 0),
      total: prev.total + 1,
    }));
  };

  const handleNextQuestion = () => {
    if (currentIndex + 1 < (assessment?.items?.length || 0)) {
      setCurrentIndex((prev) => prev + 1);
      setSelectedOption(null);
      setRevealed(false);
      requestAnimationFrame(() => {
        startTimeRef.current = performance.now();
        elapsedRef.current = 0;
      });
    } else {
      // Completed practice set
      navigate("/assessments");
    }
  };

  return (
    <MainLayout currentConcept={currentItem ? { id: currentItem.concept_id, name: currentItem.concept_name } : null}>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300">
                ✍️ Unscored Adaptive Practice
              </span>
              <span className="text-xs text-gray-400">
                Item {currentIndex + 1} of {assessment?.items?.length || 10}
              </span>
            </div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white mt-1">
              Concept Drill: {currentItem?.concept_name || "Target Mastery"}
            </h1>
          </div>

          <div className="text-right">
            <span className="text-xs text-gray-400 block">Session Accuracy</span>
            <span className="font-bold text-sm text-purple-600 dark:text-purple-400">
              {stats.total > 0 ? `${Math.round((stats.correct / stats.total) * 100)}%` : "—"} ({stats.correct}/{stats.total})
            </span>
          </div>
        </div>

        {loading && (
          <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Curating practice questions…</p>
          </div>
        )}

        {!loading && currentItem && (
          <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>Skill: {currentItem.skill_name || "General"}</span>
              <span className="capitalize">Difficulty: {currentItem.difficulty_level || "Standard"}</span>
            </div>

            <p className="text-base sm:text-lg font-medium text-gray-900 dark:text-white leading-relaxed">
              {currentItem.text}
            </p>

            {/* Options */}
            <div className="space-y-3">
              {(currentItem.options || []).map((optionText, idx) => {
                const isSelected = selectedOption === idx;
                const isCorrect = idx === currentItem.correct_option;
                let optionStyle = "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 hover:border-purple-300";

                if (revealed) {
                  if (isCorrect) {
                    optionStyle = "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 font-bold";
                  } else if (isSelected && !isCorrect) {
                    optionStyle = "border-rose-500 bg-rose-50 dark:bg-rose-950/40 text-rose-900 dark:text-rose-200";
                  } else {
                    optionStyle = "opacity-50 border-gray-200 dark:border-gray-800";
                  }
                } else if (isSelected) {
                  optionStyle = "border-purple-600 bg-purple-50 dark:bg-purple-950/40 text-purple-900 dark:text-purple-100 font-semibold";
                }

                return (
                  <button
                    key={idx}
                    type="button"
                    disabled={revealed}
                    onClick={() => handleSelectOption(idx)}
                    className={`w-full p-4 rounded-xl border text-left text-sm transition-all flex items-center justify-between ${optionStyle}`}
                  >
                    <span>{optionText}</span>
                    {revealed && isCorrect && <span className="text-emerald-600 dark:text-emerald-400 font-bold">✓ Correct</span>}
                    {revealed && isSelected && !isCorrect && <span className="text-rose-600 dark:text-rose-400 font-bold">✗ Incorrect</span>}
                  </button>
                );
              })}
            </div>

            {/* Explanation card after reveal */}
            {revealed && (
              <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900/50 space-y-2">
                <span className="text-xs font-bold text-purple-700 dark:text-purple-300 uppercase tracking-wider block">
                  Worked Explanation
                </span>
                <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  {currentItem.explanation || "No explanation provided for this practice problem."}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
              <button
                type="button"
                onClick={() => navigate("/assessments")}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                Exit Practice
              </button>

              {!revealed ? (
                <button
                  type="button"
                  disabled={selectedOption === null}
                  onClick={handleCheckAnswer}
                  className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-500/20 transition-all"
                >
                  Check Answer
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleNextQuestion}
                  className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-500/20 transition-all"
                >
                  {currentIndex + 1 < (assessment?.items?.length || 0) ? "Next Practice Question →" : "Finish Practice Set"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
