import React, { useCallback, useEffect, useRef, useState } from "react";
import { assessmentApi } from "../api/client";

/**
 * Special Test Mode Runner.
 * Implements Master Prompt Requirement 4:
 * - 30s hard limit on main question, 20s hard limit on sub-questions
 * - Countdown ring turning coral (#f43f5e) in the last 5 seconds
 * - Auto-submit as timed_out when timer reaches 0
 * - Block indicator: "Main X/5 · Sub Y/3"
 * - Dynamic server-selected sub-questions with prerequisite bias
 * - Block-end diagnostic review and final summary
 */
export default function SpecialTestRunner({ assessmentId, initialItems, onCompleted }) {
  const [currentBlockIndex, setCurrentBlockIndex] = useState(0);
  const [phase, setPhase] = useState("main"); // 'main', 'sub', 'block_end', 'completed'
  const [subIndex, setSubIndex] = useState(0);
  const [currentSubQuestions, setCurrentSubQuestions] = useState([]);
  const [mainResponseId, setMainResponseId] = useState(null);

  const [selected, setSelected] = useState(null);
  const [timeLeft, setTimeLeft] = useState(30);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Results tracking
  const [allResponses, setAllResponses] = useState([]);
  const [blockSummary, setBlockSummary] = useState(null);
  const [finalSummary, setFinalSummary] = useState(null);

  const currentMainQuestion = initialItems[currentBlockIndex];
  const currentSubQuestion = currentSubQuestions[subIndex];

  const currentItem = phase === "main" ? currentMainQuestion : currentSubQuestion;
  const timeLimit = phase === "main" ? 30 : 20;

  const shownAt = useRef(0);
  const timerRef = useRef(null);

  // Start clock when painted
  useEffect(() => {
    setSelected(null);
    const initialTime = phase === "main" ? 30 : 20;
    setTimeLeft(initialTime);

    const rafId = requestAnimationFrame(() => {
      shownAt.current = performance.now();
    });

    if (phase === "main" || phase === "sub") {
      timerRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            handleTimeout();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      cancelAnimationFrame(rafId);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [currentBlockIndex, phase, subIndex]);

  // Handle timeout auto-submission
  const handleTimeout = () => {
    recordAnswer({ timedOut: true, skipped: false });
  };

  // Record an answer (either normal submission, skip, or timeout)
  const recordAnswer = async ({ timedOut = false, skipped = false }) => {
    if (isSubmitting) return;
    if (timerRef.current) clearInterval(timerRef.current);
    setIsSubmitting(true);

    const elapsed = performance.now() - shownAt.current;
    const responsePayload = {
      question_id: currentItem.question_id,
      selected_answer: timedOut || skipped ? null : selected,
      skipped,
      timed_out: timedOut,
      response_time_ms: Math.min(timeLimit * 1000, Math.max(0, Math.round(elapsed))),
      attempt_no: 1,
      phase,
    };

    setAllResponses((prev) => [...prev, responsePayload]);

    try {
      if (phase === "main") {
        // Send main response to next-block API -> receive 3 sub-questions
        const nextBlockData = await assessmentApi.nextSpecialBlock(assessmentId, {
          assessment_id: assessmentId,
          main_response: responsePayload,
          block_index: currentBlockIndex,
        });

        setMainResponseId(nextBlockData.main_response_id);
        setCurrentSubQuestions(nextBlockData.sub_questions);
        setPhase("sub");
        setSubIndex(0);
      } else if (phase === "sub") {
        const nextSubIdx = subIndex + 1;
        if (nextSubIdx < currentSubQuestions.length) {
          setSubIndex(nextSubIdx);
        } else {
          // Finished all 3 sub-questions for this block -> block-end summary
          const currentBlockSubResponses = [...allResponses.filter((r) => r.phase === "sub"), responsePayload];
          const blockEndData = await assessmentApi.blockEndSpecial(assessmentId, {
            assessment_id: assessmentId,
            block_index: currentBlockIndex,
            main_response_id: mainResponseId,
            sub_responses: currentBlockSubResponses.slice(-3),
          });

          setBlockSummary(blockEndData);
          setPhase("block_end");
        }
      }
    } catch (err) {
      console.error("Special test block submission failed", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const advanceNextBlock = () => {
    const nextBlock = currentBlockIndex + 1;
    if (nextBlock < initialItems.length) {
      setCurrentBlockIndex(nextBlock);
      setPhase("main");
      setSubIndex(0);
      setCurrentSubQuestions([]);
      setBlockSummary(null);
    } else {
      // Completed all blocks -> Final submission
      finalizeSpecialTest();
    }
  };

  const finalizeSpecialTest = async () => {
    setIsSubmitting(true);
    try {
      const result = await assessmentApi.submit(assessmentId, allResponses);
      setFinalSummary(result);
      setPhase("completed");
    } catch (err) {
      console.error("Failed to finalize special test", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Render Block End Summary ---
  if (phase === "block_end" && blockSummary) {
    return (
      <div className="max-w-xl mx-auto bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-purple-200 dark:border-purple-900/50 p-8 text-center">
        <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
          Block {blockSummary.block_index + 1} of {initialItems.length} Complete
        </span>
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mt-2 mb-6">
          Diagnostic Block Summary
        </h3>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800">
            <span className="text-xs text-gray-500 dark:text-gray-400">Main Question</span>
            <div className="text-lg font-bold mt-1">
              {blockSummary.main_correct ? (
                <span className="text-emerald-600">✓ Correct</span>
              ) : blockSummary.main_timed_out ? (
                <span className="text-rose-500">⏱ Timed Out</span>
              ) : (
                <span className="text-amber-600">✗ Incorrect</span>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800">
            <span className="text-xs text-gray-500 dark:text-gray-400">Verification Probes</span>
            <div className="text-lg font-bold mt-1 text-gray-800 dark:text-gray-200">
              {blockSummary.sub_results.filter((s) => s.is_correct).length} / {blockSummary.sub_results.length} Correct
            </div>
          </div>
        </div>

        {blockSummary.suspected_weak_prerequisite && (
          <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 mb-6 text-left">
            <div className="flex items-center text-rose-700 dark:text-rose-400 font-semibold text-sm">
              <span className="mr-2">🔍</span> Suspected Weak Prerequisite Detected
            </div>
            <p className="text-xs text-rose-600 dark:text-rose-300 mt-1">
              Sub-question probes detected weakness in:{" "}
              <strong>{blockSummary.suspected_weak_prerequisite}</strong>. This concept will be queued for root-cause inspection.
            </p>
          </div>
        )}

        <button
          onClick={advanceNextBlock}
          className="w-full py-3.5 px-6 rounded-xl font-semibold text-sm bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-purple-500/20 transition-all"
        >
          {currentBlockIndex + 1 < initialItems.length ? "Continue to Next Block →" : "View Final Assessment Results →"}
        </button>
      </div>
    );
  }

  // --- Render Final Summary ---
  if (phase === "completed" && finalSummary) {
    return (
      <div className="max-w-xl mx-auto bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-purple-200 dark:border-purple-900/50 p-8 text-center">
        <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/40 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">
          🎯
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Special Test Completed</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-6">
          High-tempo response rhythm and prerequisite verification metrics captured.
        </p>

        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
            <span className="text-xs text-gray-400">Score</span>
            <div className="text-xl font-bold text-purple-600 dark:text-purple-400">{finalSummary.score}%</div>
          </div>
          <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
            <span className="text-xs text-gray-400">Timed Out</span>
            <div className="text-xl font-bold text-rose-500">{finalSummary.timed_out_count}</div>
          </div>
          <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
            <span className="text-xs text-gray-400">Skipped</span>
            <div className="text-xl font-bold text-amber-500">{finalSummary.skip_count}</div>
          </div>
        </div>

        <button
          onClick={() => onCompleted(finalSummary)}
          className="w-full py-3.5 px-6 rounded-xl font-semibold text-sm bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20 transition-all"
        >
          Return to Dashboard →
        </button>
      </div>
    );
  }

  if (!currentItem) return null;

  // Countdown timer circle math
  const strokeDashoffset = (1 - timeLeft / timeLimit) * 100;
  const isCoralAlert = timeLeft <= 5;

  return (
    <div
      className={`max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-2xl shadow-xl border p-8 transition-all ${
        phase === "sub"
          ? "border-indigo-200 dark:border-indigo-900/40 bg-gradient-to-b from-white to-purple-50/20 dark:from-gray-800 dark:to-purple-950/20"
          : "border-purple-200 dark:border-purple-900/50"
      }`}
    >
      {/* Block Header & Countdown */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold tracking-wide bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300">
            {phase === "main" ? `Main ${currentBlockIndex + 1}/${initialItems.length}` : `Sub-question ${subIndex + 1}/3`}
            <span className="mx-1.5 opacity-50">·</span>
            {currentItem.concept_name}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {phase === "main" ? "Core Concept Test" : "Prerequisite Verification Probe"}
          </div>
        </div>

        {/* Large Countdown Ring */}
        <div className="flex items-center space-x-2">
          <div className="relative w-14 h-14 flex items-center justify-center">
            <svg className="w-14 h-14 -rotate-90">
              <circle
                cx="28"
                cy="28"
                r="24"
                stroke="currentColor"
                strokeWidth="4"
                fill="transparent"
                className="text-gray-200 dark:text-gray-700"
              />
              <circle
                cx="28"
                cy="28"
                r="24"
                stroke="currentColor"
                strokeWidth="4"
                fill="transparent"
                strokeDasharray="150"
                strokeDashoffset={strokeDashoffset * 1.5}
                strokeLinecap="round"
                className={`transition-all duration-1000 ${
                  isCoralAlert ? "text-rose-500 animate-pulse" : "text-purple-600 dark:text-purple-400"
                }`}
              />
            </svg>
            <span
              className={`absolute font-mono font-bold text-sm ${
                isCoralAlert ? "text-rose-500" : "text-gray-800 dark:text-gray-100"
              }`}
            >
              {timeLeft}s
            </span>
          </div>
        </div>
      </div>

      {/* Question Text */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 leading-relaxed">
        {currentItem.question_text}
      </h3>

      {/* Options */}
      <div className="space-y-3 mb-8">
        {Object.entries(currentItem.options).map(([key, text]) => {
          const isSelected = selected === key;
          return (
            <label
              key={key}
              onClick={() => setSelected(key)}
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
                {key}
              </div>
              <span className="text-sm leading-relaxed">{text}</span>
            </label>
          );
        })}
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100 dark:border-gray-700">
        <button
          type="button"
          onClick={() => recordAnswer({ skipped: true })}
          className="w-full py-3 px-6 rounded-xl border-2 border-gray-300 dark:border-gray-600 font-semibold text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        >
          Skip Item
        </button>

        <button
          type="button"
          disabled={!selected || isSubmitting}
          onClick={() => recordAnswer({ skipped: false })}
          className={`w-full py-3 px-6 rounded-xl font-semibold text-sm transition-all ${
            selected && !isSubmitting
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md shadow-purple-500/20"
              : "bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed"
          }`}
        >
          {isSubmitting ? "Logging…" : "Submit Answer"}
        </button>
      </div>

      <div className="flex justify-between items-center text-xs text-gray-400 mt-4 px-1">
        <span>⏱ Auto-submits on 0s as Timed Out</span>
        <span>Strict Mode: No back-navigation</span>
      </div>
    </div>
  );
}
