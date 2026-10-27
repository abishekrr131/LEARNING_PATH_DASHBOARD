import React, { useCallback, useEffect, useRef, useState } from "react";
import { toOptionList } from "../utils/options";

/**
 * Captures the exact behaviour signal the RCT-GAT model is built on.
 * Conforms to Spec Section 31:
 *   1. Starts the clock when the item is PAINTED, not when it is fetched (requestAnimationFrame).
 *   2. Uses performance.now(), not Date.now() - preventing wall-clock jump distortion.
 *   3. Treats a skip as its own event, never as a wrong answer.
 *   4. Sends NO client timestamp. The server assigns answered_at for chronological ordering.
 */
export default function AssessmentRunner({
  assessmentId,
  items,
  onSubmitted,
  onSubmit,
  submitEndpoint,
  title = "Assessment",
}) {
  const [index, setIndex] = useState(0);
  const [responses, setResponses] = useState([]);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const shownAt = useRef(0);
  const hiddenMs = useRef(0);
  const hiddenAt = useRef(null);

  const item = items[index];
  const done = index >= items.length;

  const [showSkipConfirm, setShowSkipConfirm] = useState(false);

  // 1 + 2: Mark the paint, not the render call
  useEffect(() => {
    setSelected(null);
    setShowSkipConfirm(false);
    hiddenMs.current = 0;
    const id = requestAnimationFrame(() => {
      shownAt.current = performance.now();
    });
    return () => cancelAnimationFrame(id);
  }, [index]);

  // A tab switch is not thinking time. Subtract it rather than discarding the item.
  useEffect(() => {
    const onVis = () => {
      if (document.hidden) {
        hiddenAt.current = performance.now();
      } else if (hiddenAt.current != null) {
        hiddenMs.current += performance.now() - hiddenAt.current;
        hiddenAt.current = null;
      }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  // Warning before unload: losing half-finished assessment loses training data.
  useEffect(() => {
    const warn = (e) => {
      if (!done) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [done]);

  const record = useCallback(
    (skipped) => {
      const elapsed = performance.now() - shownAt.current - hiddenMs.current;
      setResponses((prev) => [
        ...prev,
        {
          question_id: item.question_id,
          selected_answer: skipped ? null : selected,
          skipped,
          timed_out: false,
          response_time_ms: Math.max(0, Math.round(elapsed)),
          attempt_no: 1,
        },
      ]);
      setIndex((i) => i + 1);
    },
    [item, selected]
  );

  useEffect(() => {
    if (!done || responses.length !== items.length || submitting) return;
    setSubmitting(true);

    if (onSubmit) {
      Promise.resolve(onSubmit(responses))
        .then((res) => {
          onSubmitted(res);
        })
        .catch((err) => {
          console.error("Submission failed", err);
          setSubmitting(false);
        });
      return;
    }

    const endpoint = submitEndpoint || `/api/assessments/${assessmentId}/submit`;
    fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("palp_access_token") || ""}`,
      },
      body: JSON.stringify({ responses }),
    })
      .then((r) => r.json())
      .then((res) => {
        onSubmitted(res);
      })
      .catch((err) => {
        console.error("Submission failed", err);
        setSubmitting(false);
      });
  }, [done, responses, items.length, assessmentId, onSubmitted, onSubmit, submitEndpoint, submitting]);

  if (done) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Scoring your answers…</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          Evaluating concept accuracy, response rhythm, and computing Learning Gap Score (F12).
        </p>
      </div>
    );
  }

  const progressPercent = Math.round(((index + 1) / items.length) * 100);

  return (
    <div className="max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-purple-100 dark:border-purple-900/40 p-8">
      {/* Header & Progress */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">
              {title} · {item.concept_name}
            </span>
            <span
              className={`px-2 py-0.5 rounded-full font-medium text-[10px] ${
                item.source === "gemini"
                  ? "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 border border-purple-200 dark:border-purple-800"
                  : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
              }`}
            >
              {item.source === "gemini" ? "✨ AI-Generated" : "📚 Question Bank"}
            </span>
          </div>
          {item.source_title && (
            <div className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
              <strong>Source:</strong> {item.source_title} {item.exam_year ? `(${item.exam_year})` : ""}
            </div>
          )}
          <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
            Question {index + 1} of {items.length}
          </h2>
        </div>
        <div className="text-right">
          <span className="text-xs font-mono text-gray-400">Untimed Mode</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-100 dark:bg-gray-700 h-2 rounded-full overflow-hidden mb-8">
        <div
          className="bg-gradient-to-r from-purple-500 to-indigo-600 h-full transition-all duration-300 rounded-full"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Question Text */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 leading-relaxed">
        {item.question_text || item.stem || item.text}
      </h3>

      {/* Options */}
      <div className="space-y-3 mb-8">
        {toOptionList(item.options).map((opt) => {
          const isSelected = selected === opt.key;
          return (
            <label
              key={opt.key}
              onClick={() => setSelected(opt.key)}
              className={`flex items-start p-4 rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? "border-purple-600 bg-purple-50/50 dark:bg-purple-900/20 text-purple-950 dark:text-purple-100 shadow-sm"
                  : "border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600/50 text-gray-800 dark:text-gray-200"
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs mr-3 mt-0.5 shrink-0 ${
                  isSelected
                    ? "bg-purple-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                }`}
              >
                {opt.key}
              </div>
              <span className="text-sm leading-relaxed">{opt.text}</span>
            </label>
          );
        })}
      </div>

      {/* Action Buttons: Skip Confirmation Modal / Buttons */}
      {showSkipConfirm ? (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-center space-y-3">
          <p className="text-xs font-semibold text-amber-900 dark:text-amber-200">
            Are you sure you want to skip this question?
          </p>
          <p className="text-[11px] text-amber-700 dark:text-amber-300">
            Skipped questions do not count towards demonstrated topic mastery.
          </p>
          <div className="flex justify-center gap-3">
            <button
              type="button"
              onClick={() => {
                setShowSkipConfirm(false);
                record(true);
              }}
              className="py-1.5 px-4 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all shadow-sm"
            >
              Confirm Skip
            </button>
            <button
              type="button"
              onClick={() => setShowSkipConfirm(false)}
              className="py-1.5 px-4 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-xs font-semibold hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
            >
              Resume Answering
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button
            type="button"
            onClick={() => setShowSkipConfirm(true)}
            className="w-full py-3 px-6 rounded-xl border-2 border-gray-300 dark:border-gray-600 font-semibold text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors focus:ring-2 focus:ring-purple-400"
          >
            Skip Question
          </button>

          <button
            type="button"
            disabled={!selected}
            onClick={() => record(false)}
            className={`w-full py-3 px-6 rounded-xl font-semibold text-sm transition-all focus:ring-2 focus:ring-purple-400 ${
              selected
                ? "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-purple-500/20"
                : "bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed"
            }`}
          >
            {index === items.length - 1 ? "Submit & Finish" : "Next Question →"}
          </button>
        </div>
      )}

      <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-4">
        Skipping is informative and treated as its own signal. Time is recorded in milliseconds.
      </p>
    </div>
  );
}
