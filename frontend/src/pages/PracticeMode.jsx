import React, { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { assessmentApi, targetApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { toOptionList } from "../utils/options";

export default function PracticeMode() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlMode = searchParams.get("mode");

  // Mode selection: "untimed" | "combined" | "speed"
  const [activeMode, setActiveMode] = useState(
    urlMode === "combined" || urlMode === "speed" ? urlMode : "untimed"
  );

  // Curriculum topics for topic selector
  const [targetTopics, setTargetTopics] = useState([]);
  const [selectedTopicId, setSelectedTopicId] = useState("");
  const [questionCount, setQuestionCount] = useState(5);

  // Test state
  const [inProgress, setInProgress] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Active assessment data
  const [assessment, setAssessment] = useState(null);
  const [items, setItems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // User responses & tracking
  const [answers, setAnswers] = useState({}); // { [index]: selectedOptionKey }
  const [flagged, setFlagged] = useState({}); // { [index]: boolean }
  const [revealed, setRevealed] = useState(false); // untimed: reveal explanation per question
  const [untimedStats, setUntimedStats] = useState({ correct: 0, total: 0 });

  // Combined test single 60-min countdown timer (3600 seconds)
  const [combinedTimeLeft, setCombinedTimeLeft] = useState(3600);

  // Speed test 90-sec per question timer
  const [speedTimeLeft, setSpeedTimeLeft] = useState(90);

  // Speed test sub-questions diagnostic flow
  const [isDiagnosticSubFlow, setIsDiagnosticSubFlow] = useState(false);
  const [subQuestionsData, setSubQuestionsData] = useState(null);
  const [subQuestionIndex, setSubQuestionIndex] = useState(0);
  const [subResponses, setSubResponses] = useState([]);
  const [selectedSubOption, setSelectedSubOption] = useState(null);
  const [rootCauseResult, setRootCauseResult] = useState(null);
  const [sessionRootCauses, setSessionRootCauses] = useState([]);

  // Load target curriculum topics for the selector dropdown
  useEffect(() => {
    const targetId = profile?.target_id || 1;
    targetApi
      .getDetail(targetId)
      .then((data) => {
        const topics = [];
        (data.skills || []).forEach((s) => {
          (s.topics || []).forEach((t) => {
            topics.push({
              id: t.id,
              name: t.name,
              skillName: s.name,
            });
          });
        });
        setTargetTopics(topics);
      })
      .catch((err) => {
        console.warn("Failed to fetch target topics:", err);
      });
  }, [profile?.target_id]);

  // Adjust default question count when switching modes
  const handleModeChange = (mode) => {
    setActiveMode(mode);
    setError(null);
    if (mode === "combined") {
      setQuestionCount(40);
    } else if (mode === "speed") {
      setQuestionCount(10);
    } else {
      setQuestionCount(5);
    }
  };

  // Start assessment session
  const startSession = () => {
    setLoading(true);
    setError(null);
    setAnswers({});
    setFlagged({});
    setRevealed(false);
    setUntimedStats({ correct: 0, total: 0 });
    setIsDiagnosticSubFlow(false);
    setRootCauseResult(null);
    setSessionRootCauses([]);

    const payload = {
      type: "practice",
      target_id: profile?.target_id || 1,
      practice_mode: activeMode,
      count:
        activeMode === "combined"
          ? 40
          : activeMode === "speed"
          ? questionCount || 10
          : questionCount || 5,
      topic_id:
        activeMode === "untimed" && selectedTopicId
          ? parseInt(selectedTopicId, 10)
          : undefined,
    };

    assessmentApi
      .start(payload)
      .then((data) => {
        setAssessment(data);
        const qItems = data.items || [];
        setItems(qItems);
        setCurrentIndex(0);
        setInProgress(true);
        setCompleted(false);

        if (activeMode === "combined") {
          setCombinedTimeLeft(3600);
        } else if (activeMode === "speed") {
          setSpeedTimeLeft(90);
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to initialize practice session.");
      })
      .finally(() => setLoading(false));
  };

  // 60-min timer for Combined Test
  useEffect(() => {
    if (!inProgress || completed || activeMode !== "combined") return;
    const timer = setInterval(() => {
      setCombinedTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleSubmitCombinedTest();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [inProgress, completed, activeMode]);

  // 90s timer for Speed Test
  useEffect(() => {
    if (
      !inProgress ||
      completed ||
      activeMode !== "speed" ||
      isDiagnosticSubFlow
    )
      return;
    const timer = setInterval(() => {
      setSpeedTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleSpeedTimeout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inProgress, completed, activeMode, isDiagnosticSubFlow, currentIndex]);

  // Current item helpers
  const currentItem = items[currentIndex];
  const optionList = currentItem ? toOptionList(currentItem.options) : [];

  // Untimed mode: Select option
  const handleSelectUntimedOption = (key) => {
    if (revealed) return;
    setAnswers((prev) => ({ ...prev, [currentIndex]: key }));
  };

  // Untimed mode: Check answer
  const handleCheckUntimedAnswer = () => {
    const selected = answers[currentIndex];
    if (selected === undefined || !currentItem) return;
    const isCorrect =
      String(selected).toUpperCase() ===
      String(currentItem.correct_option || "").toUpperCase();
    setRevealed(true);
    setUntimedStats((prev) => ({
      correct: prev.correct + (isCorrect ? 1 : 0),
      total: prev.total + 1,
    }));
  };

  // Untimed mode: Next question
  const handleNextUntimedQuestion = () => {
    if (currentIndex + 1 < items.length) {
      setCurrentIndex((prev) => prev + 1);
      setRevealed(false);
    } else {
      setCompleted(true);
      setInProgress(false);
    }
  };

  // Combined mode: Select option
  const handleSelectCombinedOption = (key) => {
    setAnswers((prev) => ({ ...prev, [currentIndex]: key }));
  };

  // Combined mode: Toggle flagged
  const toggleFlagged = (idx) => {
    setFlagged((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  // Combined mode: Submit test
  const handleSubmitCombinedTest = () => {
    setCompleted(true);
    setInProgress(false);
  };

  // Speed test: Option selected
  const handleSelectSpeedOption = (key) => {
    setAnswers((prev) => ({ ...prev, [currentIndex]: key }));
  };

  // Speed test: Submit answer for current question
  const handleSubmitSpeedAnswer = () => {
    if (!currentItem) return;
    const chosen = answers[currentIndex];
    const isCorrect =
      String(chosen).toUpperCase() ===
      String(currentItem.correct_option || "").toUpperCase();

    if (isCorrect) {
      // Correct! Proceed to next question
      advanceSpeedQuestion();
    } else {
      // Incorrect! Trigger 3-stage diagnostic sub-questions
      triggerDiagnosticSubQuestions();
    }
  };

  // Speed test: Timeout triggers diagnostic flow
  const handleSpeedTimeout = () => {
    triggerDiagnosticSubQuestions();
  };

  // Combined mode: Next question with prerequisite diagnostic sub-questions on error
  const handleNextCombinedQuestion = () => {
    const chosen = answers[currentIndex];
    if (chosen !== undefined && currentItem) {
      const isCorrect =
        String(chosen).toUpperCase() ===
        String(currentItem.correct_option || "").toUpperCase();
      if (!isCorrect) {
        triggerDiagnosticSubQuestions("combined");
        return;
      }
    }
    if (currentIndex + 1 < items.length) {
      setCurrentIndex((prev) => prev + 1);
    }
  };

  // Trigger diagnostic sub-questions for test failure
  const triggerDiagnosticSubQuestions = (targetMode = activeMode) => {
    if (!currentItem) return;
    setLoading(true);
    const chosen = answers[currentIndex];
    assessmentApi
      .getSubQuestions(currentItem.question_id, {
        assessment_id: assessment?.assessment_id,
        selected_answer: chosen,
        response_time_ms: targetMode === "speed" ? (90 - speedTimeLeft) * 1000 : 15000,
        timed_out: targetMode === "speed" && speedTimeLeft <= 1,
      })
      .then((data) => {
        if (data && data.has_sub_questions && data.sub_questions?.length > 0) {
          setSubQuestionsData(data);
          setSubQuestionIndex(0);
          setSubResponses([]);
          setSelectedSubOption(null);
          setRootCauseResult(null);
          setIsDiagnosticSubFlow(true);
        } else {
          // No sub-questions available, log gap and advance
          setSessionRootCauses((prev) => [
            ...prev,
            {
              topic: currentItem.topic_name || currentItem.concept_name,
              stem: currentItem.question_text,
              gap: targetMode === "speed" ? "Speed / Accuracy Gap (Unclassified)" : "Prerequisite Knowledge Gap",
              studyTask: "Review topic fundamentals and prerequisite dependencies",
            },
          ]);
          advanceQuestion(targetMode);
        }
      })
      .catch((err) => {
        console.warn("Sub questions error:", err);
        advanceQuestion(targetMode);
      })
      .finally(() => setLoading(false));
  };

  // Handle answering sub-question
  const handleConfirmSubAnswer = () => {
    if (selectedSubOption === null || !subQuestionsData) return;
    const currentSub = subQuestionsData.sub_questions[subQuestionIndex];
    const isSubCorrect =
      String(selectedSubOption).toUpperCase() ===
      String(currentSub.correct_option || "").toUpperCase();

    const updatedResponses = [
      ...subResponses,
      {
        question_id: currentSub.id,
        stage: currentSub.stage,
        selected_answer: selectedSubOption,
        is_correct: isSubCorrect,
      },
    ];
    setSubResponses(updatedResponses);
    setSelectedSubOption(null);

    if (subQuestionIndex + 1 < subQuestionsData.sub_questions.length) {
      setSubQuestionIndex((prev) => prev + 1);
    } else {
      // Evaluate sub-responses
      const formulaResp = updatedResponses.find((r) =>
        r.stage?.includes("formula")
      );
      const subResp = updatedResponses.find((r) =>
        r.stage?.includes("substitution")
      );
      const calcResp = updatedResponses.find((r) =>
        r.stage?.includes("calculation")
      );

      const allSubCorrect = updatedResponses.every((r) => r.is_correct);

      const evalPayload = {
        question_id: currentItem.question_id,
        assessment_id: assessment?.assessment_id,
        parent_response_id: subQuestionsData?.parent_response_id,
        formula_correct: formulaResp ? formulaResp.is_correct : allSubCorrect,
        substitution_correct: subResp ? subResp.is_correct : allSubCorrect,
        calculation_correct: calcResp ? calcResp.is_correct : allSubCorrect,
        calculation_time_ms: 12000,
        sub_responses: updatedResponses,
      };

      assessmentApi
        .evaluateRootCause(evalPayload)
        .then((res) => {
          setRootCauseResult(res);
          setSessionRootCauses((prev) => [
            ...prev,
            {
              topic: currentItem.topic_name || currentItem.concept_name,
              stem: currentItem.question_text,
              gap: res.gap_type || "Conceptual Gap",
              studyTask:
                res.study_task ||
                "Focus on step-by-step problem deconstruction",
            },
          ]);
        })
        .catch((err) => {
          console.warn("Root cause evaluation error:", err);
          setRootCauseResult({
            gap_type: "Identified Cognitive Gap",
            study_task: "Review worked solutions in detail",
          });
        });
    }
  };

  // Continue to next question after reviewing root-cause diagnosis
  const advanceQuestion = (mode = activeMode) => {
    setIsDiagnosticSubFlow(false);
    setSubQuestionsData(null);
    setRootCauseResult(null);
    if (currentIndex + 1 < items.length) {
      setCurrentIndex((prev) => prev + 1);
      if (mode === "speed") {
        setSpeedTimeLeft(90);
      }
    } else {
      setCompleted(true);
      setInProgress(false);
    }
  };

  const advanceSpeedQuestion = () => advanceQuestion("speed");

  // Format seconds into MM:SS
  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Compute results for combined test
  const calculateCombinedResults = () => {
    let totalCorrect = 0;
    const bySkill = {};

    items.forEach((item, idx) => {
      const chosen = answers[idx];
      const isCorrect =
        chosen !== undefined &&
        String(chosen).toUpperCase() ===
          String(item.correct_option || "").toUpperCase();
      if (isCorrect) totalCorrect += 1;

      const skill = item.skill_name || "General";
      if (!bySkill[skill]) {
        bySkill[skill] = { correct: 0, total: 0 };
      }
      bySkill[skill].total += 1;
      if (isCorrect) bySkill[skill].correct += 1;
    });

    return { totalCorrect, bySkill };
  };

  return (
    <MainLayout
      currentConcept={
        currentItem
          ? { id: currentItem.concept_id, name: currentItem.concept_name }
          : null
      }
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Top Header & Mode Switcher (visible when not actively in a test) */}
        {!inProgress && !completed && (
          <div className="bg-white dark:bg-gray-900 p-6 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Practice & Mock Test Hub
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  Choose a practice mode to train deliberately or test under
                  exam conditions.
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate("/assessments")}
                className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 self-start sm:self-auto"
              >
                ← Return to Assessments
              </button>
            </div>

            {/* Mode Tabs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                type="button"
                data-testid="mode-tab-untimed"
                onClick={() => handleModeChange("untimed")}
                className={`p-4 rounded-xl border text-left transition-all ${
                  activeMode === "untimed"
                    ? "border-purple-600 bg-purple-50 dark:bg-purple-950/40 ring-2 ring-purple-600/20"
                    : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-gray-50/50 dark:bg-gray-800/40"
                }`}
              >
                <div className="text-xl mb-1">📖</div>
                <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                  Practice (Untimed)
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  Topic drill with instant worked explanations after every
                  question. No timer.
                </p>
              </button>

              <button
                type="button"
                data-testid="mode-tab-combined"
                onClick={() => handleModeChange("combined")}
                className={`p-4 rounded-xl border text-left transition-all ${
                  activeMode === "combined"
                    ? "border-purple-600 bg-purple-50 dark:bg-purple-950/40 ring-2 ring-purple-600/20"
                    : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-gray-50/50 dark:bg-gray-800/40"
                }`}
              >
                <div className="text-xl mb-1">⏱️</div>
                <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                  Combined Test
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  Full exam simulation. Max 40 questions, 60-min single countdown,
                  question navigator, section breakdown.
                </p>
              </button>

              <button
                type="button"
                data-testid="mode-tab-speed"
                onClick={() => handleModeChange("speed")}
                className={`p-4 rounded-xl border text-left transition-all ${
                  activeMode === "speed"
                    ? "border-purple-600 bg-purple-50 dark:bg-purple-950/40 ring-2 ring-purple-600/20"
                    : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-gray-50/50 dark:bg-gray-800/40"
                }`}
              >
                <div className="text-xl mb-1">⚡</div>
                <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                  Speed Test
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  90s timer per question. Wrong answers instantly ask 3 sub-questions
                  to diagnose root causes.
                </p>
              </button>
            </div>

            {/* Mode-Specific Configuration */}
            <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 space-y-4">
              {activeMode === "untimed" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      Filter by Topic (Optional)
                    </label>
                    <select
                      value={selectedTopicId}
                      onChange={(e) => setSelectedTopicId(e.target.value)}
                      className="w-full text-xs p-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                    >
                      <option value="">All Topics (Adaptive)</option>
                      {targetTopics.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.skillName} → {t.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      Number of Questions
                    </label>
                    <select
                      value={questionCount}
                      onChange={(e) =>
                        setQuestionCount(parseInt(e.target.value, 10))
                      }
                      className="w-full text-xs p-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                    >
                      <option value={5}>5 Questions (Quick Drill)</option>
                      <option value={10}>10 Questions (Standard Drill)</option>
                      <option value={15}>15 Questions (Extended Practice)</option>
                    </select>
                  </div>
                </div>
              )}

              {activeMode === "combined" && (
                <div className="space-y-2 text-xs text-gray-600 dark:text-gray-400">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-purple-600 dark:text-purple-400">
                      Structure:
                    </span>
                    <span>
                      Up to 40 questions allotted by target skill weights (Quantitative,
                      Reasoning, English)
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-purple-600 dark:text-purple-400">
                      Timer:
                    </span>
                    <span>
                      Single 60-minute countdown (auto-submits when time expires)
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-purple-600 dark:text-purple-400">
                      Features:
                    </span>
                    <span>
                      Interactive 1..40 Question Palette, jump to any question, flag for
                      review
                    </span>
                  </div>
                </div>
              )}

              {activeMode === "speed" && (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                        Number of Speed Drills
                      </label>
                      <select
                        value={questionCount}
                        onChange={(e) =>
                          setQuestionCount(parseInt(e.target.value, 10))
                        }
                        className="w-full text-xs p-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                      >
                        <option value={5}>5 Drills</option>
                        <option value={10}>10 Drills</option>
                      </select>
                    </div>
                  </div>
                  <p className="text-xs text-amber-600 dark:text-amber-400">
                    ⚡ 90 seconds per question. On wrong answer or timeout, you will
                    immediately be guided through 3 diagnostic sub-questions (Formula,
                    Substitution, Calculation) to uncover the exact cognitive cause.
                  </p>
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  data-testid="start-practice-btn"
                  onClick={startSession}
                  disabled={loading}
                  className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md transition-all flex items-center gap-2"
                >
                  {loading && (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  )}
                  {activeMode === "combined"
                    ? "Start Combined Test (60 min) →"
                    : activeMode === "speed"
                    ? "Start Speed Drills (90s) →"
                    : "Start Untimed Practice →"}
                </button>
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs">
                ⚠️ {error}
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* ACTIVE SESSION: UNTIMED PRACTICE                         */}
        {/* ======================================================== */}
        {inProgress && !completed && activeMode === "untimed" && currentItem && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300">
                  📖 Untimed Practice Drill
                </span>
                <span className="text-xs text-gray-400 ml-2">
                  Question {currentIndex + 1} of {items.length}
                </span>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white mt-1">
                  {currentItem.topic_name || currentItem.concept_name}
                </h2>
              </div>
              <div className="text-right">
                <span className="text-xs text-gray-400 block">Session Accuracy</span>
                <span className="font-bold text-sm text-purple-600 dark:text-purple-400">
                  {untimedStats.total > 0
                    ? `${Math.round(
                        (untimedStats.correct / untimedStats.total) * 100
                      )}%`
                    : "—"}{" "}
                  ({untimedStats.correct}/{untimedStats.total})
                </span>
              </div>
            </div>

            <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6">
              <p className="text-base sm:text-lg font-medium text-gray-900 dark:text-white leading-relaxed">
                {currentItem.question_text || currentItem.stem}
              </p>

              {/* Options */}
              <div className="space-y-3">
                {optionList.map((opt) => {
                  const isSelected = answers[currentIndex] === opt.key;
                  const isCorrect =
                    String(opt.key).toUpperCase() ===
                    String(currentItem.correct_option || "").toUpperCase();

                  let optStyle =
                    "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 hover:border-purple-300";
                  if (revealed) {
                    if (isCorrect) {
                      optStyle =
                        "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 font-bold";
                    } else if (isSelected && !isCorrect) {
                      optStyle =
                        "border-rose-500 bg-rose-50 dark:bg-rose-950/40 text-rose-900 dark:text-rose-200";
                    } else {
                      optStyle = "opacity-50 border-gray-200 dark:border-gray-800";
                    }
                  } else if (isSelected) {
                    optStyle =
                      "border-purple-600 bg-purple-50 dark:bg-purple-950/40 text-purple-900 dark:text-purple-100 font-semibold";
                  }

                  return (
                    <button
                      key={opt.key}
                      type="button"
                      disabled={revealed}
                      onClick={() => handleSelectUntimedOption(opt.key)}
                      className={`w-full p-4 rounded-xl border text-left text-sm transition-all flex items-center justify-between ${optStyle}`}
                    >
                      <div className="flex items-center space-x-3">
                        <span className="w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shrink-0 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                          {opt.key}
                        </span>
                        <span>{opt.text}</span>
                      </div>
                      {revealed && isCorrect && (
                        <span className="text-emerald-600 dark:text-emerald-400 font-bold text-xs">
                          ✓ Correct
                        </span>
                      )}
                      {revealed && isSelected && !isCorrect && (
                        <span className="text-rose-600 dark:text-rose-400 font-bold text-xs">
                          ✗ Incorrect
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Worked Explanation Card */}
              {revealed && (
                <div
                  data-testid="worked-explanation-card"
                  className="p-4 rounded-xl bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900/50 space-y-2 animate-fadeIn"
                >
                  <span className="text-xs font-bold text-purple-700 dark:text-purple-300 uppercase tracking-wider block">
                    Worked Explanation
                  </span>
                  <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                    {currentItem.explanation || "Standard syllabus rationale."}
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
                <button
                  type="button"
                  onClick={() => {
                    setInProgress(false);
                    setCompleted(false);
                  }}
                  className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  Exit Practice
                </button>

                {!revealed ? (
                  <button
                    type="button"
                    data-testid="check-answer-btn"
                    disabled={answers[currentIndex] === undefined}
                    onClick={handleCheckUntimedAnswer}
                    className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                  >
                    Check Answer
                  </button>
                ) : (
                  <button
                    type="button"
                    data-testid="next-untimed-btn"
                    onClick={handleNextUntimedQuestion}
                    className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                  >
                    {currentIndex + 1 < items.length
                      ? "Next Question →"
                      : "Finish Practice Set"}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* ACTIVE SESSION: COMBINED TEST (60m, 40 Qs, Palette)      */}
        {/* ======================================================== */}
        {inProgress && !completed && activeMode === "combined" && currentItem && (
          <div className="space-y-6">
            {/* Top Bar with 60-min timer and submit button */}
            <div className="flex items-center justify-between bg-white dark:bg-gray-900 p-4 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm">
              <div className="flex items-center gap-3">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300">
                  ⏱️ Combined Test
                </span>
                <span className="text-xs font-medium text-gray-500">
                  Section: {currentItem.skill_name || "General"} · Topic:{" "}
                  {currentItem.topic_name || currentItem.concept_name}
                </span>
              </div>

              <div className="flex items-center gap-4">
                {/* 60-min Countdown Timer */}
                <div
                  data-testid="combined-countdown"
                  className={`px-3 py-1.5 rounded-xl font-mono text-sm font-bold flex items-center gap-1.5 ${
                    combinedTimeLeft < 60
                      ? "bg-rose-100 dark:bg-rose-950/80 text-rose-600 animate-pulse"
                      : combinedTimeLeft < 300
                      ? "bg-amber-100 dark:bg-amber-950/60 text-amber-600"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200"
                  }`}
                >
                  <span>⏳</span>
                  <span>{formatTime(combinedTimeLeft)}</span>
                </div>

                <button
                  type="button"
                  data-testid="submit-combined-test-btn"
                  onClick={handleSubmitCombinedTest}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                >
                  Submit Test
                </button>
              </div>
            </div>

            {/* Question Navigator Palette (1..40) */}
            <div
              data-testid="question-palette"
              className="bg-white dark:bg-gray-900 p-4 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-3"
            >
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span className="font-semibold text-gray-700 dark:text-gray-300">
                  Question Palette ({Object.keys(answers).length}/{items.length}{" "}
                  Answered)
                </span>
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />{" "}
                    Answered
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />{" "}
                    Review
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-gray-300 dark:bg-gray-700" />{" "}
                    Unanswered
                  </span>
                </div>
              </div>

              {/* Navigator buttons */}
              <div className="grid grid-cols-10 sm:grid-cols-20 gap-1.5">
                {items.map((it, idx) => {
                  const isCurrent = idx === currentIndex;
                  const isAnswered = answers[idx] !== undefined;
                  const isFlagged = flagged[idx];

                  let btnStyle =
                    "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700";
                  if (isFlagged) {
                    btnStyle =
                      "bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-200 border-amber-400";
                  } else if (isAnswered) {
                    btnStyle =
                      "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border-emerald-400";
                  }

                  return (
                    <button
                      key={idx}
                      type="button"
                      data-testid={`palette-btn-${idx + 1}`}
                      onClick={() => setCurrentIndex(idx)}
                      className={`h-8 rounded-lg text-xs font-bold border transition-all flex items-center justify-center ${btnStyle} ${
                        isCurrent
                          ? "ring-2 ring-purple-600 font-extrabold scale-105"
                          : ""
                      }`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>

            {isDiagnosticSubFlow ? (
              // Diagnostic Sub-Questions Interactive Flow in Combined Mode
              <div
                data-testid="sub-questions-flow"
                className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border-2 border-rose-300 dark:border-rose-900 shadow-lg space-y-6 animate-fadeIn"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300">
                      🚨 Prerequisite Diagnostic Triggered
                    </span>
                    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-1">
                      Original Problem: "{currentItem.question_text?.slice(0, 70)}..."
                    </h2>
                  </div>
                  <span className="text-xs font-bold text-gray-400">
                    Step {subQuestionIndex + 1} of{" "}
                    {subQuestionsData?.sub_questions?.length || 3}
                  </span>
                </div>

                {rootCauseResult ? (
                  <div
                    data-testid="root-cause-result-banner"
                    className="p-5 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 space-y-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🎯</span>
                      <h3 className="font-bold text-sm text-purple-900 dark:text-purple-200">
                        Cognitive Gap Identified: {rootCauseResult.gap_type}
                      </h3>
                    </div>
                    <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                      {rootCauseResult.study_task}
                    </p>
                    <div className="pt-2">
                      <button
                        type="button"
                        data-testid="continue-speed-btn"
                        onClick={() => advanceQuestion("combined")}
                        className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                      >
                        Continue to Next Combined Question →
                      </button>
                    </div>
                  </div>
                ) : (
                  subQuestionsData?.sub_questions?.[subQuestionIndex] && (
                    <div className="space-y-4">
                      <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-800">
                        <span className="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 block mb-1">
                          Stage:{" "}
                          {subQuestionsData.sub_questions[subQuestionIndex].stage}
                        </span>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {subQuestionsData.sub_questions[subQuestionIndex].stem}
                        </p>
                      </div>

                      <div className="space-y-2">
                        {toOptionList(
                          subQuestionsData.sub_questions[subQuestionIndex].options
                        ).map((opt) => (
                          <button
                            key={opt.key}
                            type="button"
                            onClick={() => setSelectedSubOption(opt.key)}
                            className={`w-full p-3 rounded-xl border text-left text-xs transition-all flex items-center justify-between ${
                              selectedSubOption === opt.key
                                ? "border-purple-600 bg-purple-50 dark:bg-purple-950/40 font-semibold text-purple-900 dark:text-purple-100"
                                : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-purple-300"
                            }`}
                          >
                            <span className="flex items-center gap-2">
                              <span className="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center font-bold text-[10px]">
                                {opt.key}
                              </span>
                              <span>{opt.text}</span>
                            </span>
                            {selectedSubOption === opt.key && (
                              <span className="text-purple-600 text-xs font-bold">
                                ✓
                              </span>
                            )}
                          </button>
                        ))}
                      </div>

                      <div className="flex justify-end pt-2">
                        <button
                          type="button"
                          data-testid="confirm-sub-btn"
                          disabled={selectedSubOption === null}
                          onClick={handleConfirmSubAnswer}
                          className="px-5 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                        >
                          Verify Sub-Step →
                        </button>
                      </div>
                    </div>
                  )
                )}
              </div>
            ) : (
              /* Current Question Card */
              <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6">
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>
                    Question {currentIndex + 1} of {items.length}
                  </span>
                  <button
                    type="button"
                    data-testid="flag-review-btn"
                    onClick={() => toggleFlagged(currentIndex)}
                    className={`px-3 py-1 rounded-lg border text-xs font-medium transition-all ${
                      flagged[currentIndex]
                        ? "bg-amber-50 dark:bg-amber-950/40 border-amber-400 text-amber-700 dark:text-amber-300"
                        : "border-gray-200 dark:border-gray-700 text-gray-500 hover:border-gray-300"
                    }`}
                  >
                    {flagged[currentIndex] ? "★ Flagged for Review" : "☆ Flag for Review"}
                  </button>
                </div>

                <p className="text-base sm:text-lg font-medium text-gray-900 dark:text-white leading-relaxed">
                  {currentItem.question_text || currentItem.stem}
                </p>

                {/* Options */}
                <div className="space-y-3">
                  {optionList.map((opt) => {
                    const isSelected = answers[currentIndex] === opt.key;
                    return (
                      <button
                        key={opt.key}
                        type="button"
                        data-testid={`option-btn-${opt.key}`}
                        onClick={() => handleSelectCombinedOption(opt.key)}
                        className={`w-full p-4 rounded-xl border text-left text-sm transition-all flex items-center justify-between ${
                          isSelected
                            ? "border-purple-600 bg-purple-50 dark:bg-purple-950/40 text-purple-900 dark:text-purple-100 font-semibold"
                            : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 hover:border-purple-300"
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <span className="w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shrink-0 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                            {opt.key}
                          </span>
                          <span>{opt.text}</span>
                        </div>
                        {isSelected && (
                          <span className="text-purple-600 dark:text-purple-400 font-bold text-xs">
                            ● Selected
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Navigation controls */}
                <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
                  <button
                    type="button"
                    data-testid="prev-combined-btn"
                    disabled={currentIndex === 0}
                    onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                    className="px-4 py-2 text-xs font-semibold rounded-xl border border-gray-200 dark:border-gray-700 disabled:opacity-30 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    ← Previous
                  </button>

                  <div className="flex items-center gap-2">
                    {currentIndex + 1 < items.length ? (
                      <button
                        type="button"
                        data-testid="next-combined-btn"
                        onClick={handleNextCombinedQuestion}
                        className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                      >
                        Next →
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleSubmitCombinedTest}
                        className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                      >
                        Finish & Submit Test
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* ACTIVE SESSION: SPEED TEST (90s + Sub-Questions)        */}
        {/* ======================================================== */}
        {inProgress && !completed && activeMode === "speed" && currentItem && (
          <div className="space-y-6">
            {!isDiagnosticSubFlow ? (
              // Main Speed Question
              <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">
                      ⚡ Speed Drill {currentIndex + 1} of {items.length}
                    </span>
                    <h2 className="text-base font-bold text-gray-900 dark:text-white mt-1">
                      {currentItem.topic_name || currentItem.concept_name}
                    </h2>
                  </div>

                  {/* 90-sec countdown badge */}
                  <div
                    data-testid="speed-countdown"
                    className={`px-4 py-2 rounded-xl font-mono text-base font-bold flex items-center gap-1.5 ${
                      speedTimeLeft <= 15
                        ? "bg-rose-100 dark:bg-rose-950/80 text-rose-600 animate-pulse ring-2 ring-rose-500/50"
                        : "bg-amber-50 dark:bg-amber-950/40 text-amber-600"
                    }`}
                  >
                    <span>⚡</span>
                    <span>{speedTimeLeft}s</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-100 dark:bg-gray-800 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-1000 ${
                      speedTimeLeft <= 15 ? "bg-rose-500" : "bg-amber-500"
                    }`}
                    style={{ width: `${(speedTimeLeft / 90) * 100}%` }}
                  />
                </div>

                <p className="text-base sm:text-lg font-medium text-gray-900 dark:text-white leading-relaxed">
                  {currentItem.question_text || currentItem.stem}
                </p>

                {/* Options */}
                <div className="space-y-3">
                  {optionList.map((opt) => {
                    const isSelected = answers[currentIndex] === opt.key;
                    return (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() => handleSelectSpeedOption(opt.key)}
                        className={`w-full p-4 rounded-xl border text-left text-sm transition-all flex items-center justify-between ${
                          isSelected
                            ? "border-amber-500 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-100 font-semibold"
                            : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 hover:border-amber-300"
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <span className="w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shrink-0 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                            {opt.key}
                          </span>
                          <span>{opt.text}</span>
                        </div>
                        {isSelected && (
                          <span className="text-amber-600 dark:text-amber-400 font-bold text-xs">
                            ● Selected
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
                  <span className="text-xs text-gray-400">
                    Submit quickly before time expires!
                  </span>
                  <button
                    type="button"
                    data-testid="submit-speed-answer-btn"
                    disabled={answers[currentIndex] === undefined}
                    onClick={handleSubmitSpeedAnswer}
                    className="px-6 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                  >
                    Confirm Answer →
                  </button>
                </div>
              </div>
            ) : (
              // Diagnostic Sub-Questions Interactive Flow
              <div
                data-testid="sub-questions-flow"
                className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border-2 border-rose-300 dark:border-rose-900 shadow-lg space-y-6 animate-fadeIn"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300">
                      🚨 Root Cause Diagnosis Triggered
                    </span>
                    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mt-1">
                      Original Problem: "{currentItem.question_text?.slice(0, 70)}..."
                    </h2>
                  </div>
                  <span className="text-xs font-bold text-gray-400">
                    Step {subQuestionIndex + 1} of{" "}
                    {subQuestionsData?.sub_questions?.length || 3}
                  </span>
                </div>

                {rootCauseResult ? (
                  // Diagnosis Result Banner
                  <div
                    data-testid="root-cause-result-banner"
                    className="p-5 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 space-y-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🎯</span>
                      <h3 className="font-bold text-sm text-purple-900 dark:text-purple-200">
                        Cognitive Gap Identified: {rootCauseResult.gap_type}
                      </h3>
                    </div>
                    <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                      {rootCauseResult.study_task}
                    </p>
                    <div className="pt-2">
                      <button
                        type="button"
                        data-testid="continue-speed-btn"
                        onClick={advanceSpeedQuestion}
                        className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                      >
                        Continue to Next Speed Drill →
                      </button>
                    </div>
                  </div>
                ) : (
                  // Active sub-question
                  subQuestionsData?.sub_questions?.[subQuestionIndex] && (
                    <div className="space-y-4">
                      <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-800">
                        <span className="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 block mb-1">
                          Stage:{" "}
                          {subQuestionsData.sub_questions[subQuestionIndex].stage}
                        </span>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {subQuestionsData.sub_questions[subQuestionIndex].stem}
                        </p>
                      </div>

                      <div className="space-y-2">
                        {toOptionList(
                          subQuestionsData.sub_questions[subQuestionIndex].options
                        ).map((opt) => (
                          <button
                            key={opt.key}
                            type="button"
                            onClick={() => setSelectedSubOption(opt.key)}
                            className={`w-full p-3 rounded-xl border text-left text-xs transition-all flex items-center justify-between ${
                              selectedSubOption === opt.key
                                ? "border-purple-600 bg-purple-50 dark:bg-purple-950/40 font-semibold text-purple-900 dark:text-purple-100"
                                : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-purple-300"
                            }`}
                          >
                            <span className="flex items-center gap-2">
                              <span className="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center font-bold text-[10px]">
                                {opt.key}
                              </span>
                              <span>{opt.text}</span>
                            </span>
                            {selectedSubOption === opt.key && (
                              <span className="text-purple-600 text-xs font-bold">
                                ✓
                              </span>
                            )}
                          </button>
                        ))}
                      </div>

                      <div className="flex justify-end pt-2">
                        <button
                          type="button"
                          data-testid="confirm-sub-btn"
                          disabled={selectedSubOption === null}
                          onClick={handleConfirmSubAnswer}
                          className="px-5 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                        >
                          Verify Sub-Step →
                        </button>
                      </div>
                    </div>
                  )
                )}
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* COMPLETED / RESULTS VIEW                                 */}
        {/* ======================================================== */}
        {completed && (
          <div
            data-testid="practice-results-view"
            className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6 animate-fadeIn"
          >
            <div className="text-center space-y-2">
              <span className="text-4xl">🎉</span>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Session Completed!
              </h2>
              <p className="text-xs text-gray-500">
                {activeMode === "combined"
                  ? "Combined Test Submission & Section Breakdown"
                  : activeMode === "speed"
                  ? "Speed Drill Results & Diagnosed Root Causes"
                  : "Untimed Practice Set Results"}
              </p>
            </div>

            {/* Combined Mode: Section Breakdown */}
            {activeMode === "combined" && (() => {
              const res = calculateCombinedResults();
              const pct = Math.round((res.totalCorrect / (items.length || 1)) * 100);
              return (
                <div className="space-y-6">
                  {/* Overall score banner */}
                  <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900/50 flex items-center justify-between">
                    <div>
                      <span className="text-xs text-purple-700 dark:text-purple-300 font-bold uppercase tracking-wider block">
                        Total Mock Exam Score
                      </span>
                      <span className="text-2xl font-black text-gray-900 dark:text-white">
                        {res.totalCorrect} / {items.length} ({pct}%)
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      Time Remaining: {formatTime(combinedTimeLeft)}
                    </span>
                  </div>

                  {/* Section Breakdown Grid */}
                  <div
                    data-testid="section-breakdown"
                    className="space-y-3"
                  >
                    <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                      Section-Wise Performance Breakdown
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {Object.entries(res.bySkill).map(([skill, sData]) => {
                        const sPct = Math.round(
                          (sData.correct / (sData.total || 1)) * 100
                        );
                        return (
                          <div
                            key={skill}
                            className="p-4 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/40 space-y-2"
                          >
                            <span className="text-xs font-bold text-gray-700 dark:text-gray-300 block truncate">
                              {skill}
                            </span>
                            <div className="flex items-baseline justify-between">
                              <span className="text-lg font-bold text-gray-900 dark:text-white">
                                {sData.correct} / {sData.total}
                              </span>
                              <span className="text-xs font-semibold text-purple-600 dark:text-purple-400">
                                {sPct}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 h-1.5 rounded-full overflow-hidden">
                              <div
                                className="bg-purple-600 h-full rounded-full"
                                style={{ width: `${sPct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Speed Mode: Root Causes Identified */}
            {activeMode === "speed" && (
              <div className="space-y-4">
                <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                  Cognitive Root Causes Discovered
                </h3>
                {sessionRootCauses.length === 0 ? (
                  <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/50 text-xs text-emerald-800 dark:text-emerald-200 font-medium">
                    ✨ Perfect run! Zero cognitive root-cause bottlenecks detected
                    during this speed session.
                  </div>
                ) : (
                  <div
                    data-testid="causes-found-list"
                    className="space-y-2"
                  >
                    {sessionRootCauses.map((cause, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/50 dark:bg-rose-950/20 space-y-1"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-rose-700 dark:text-rose-300">
                            {cause.topic}
                          </span>
                          <span className="font-semibold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/60 text-rose-800 dark:text-rose-200 text-[10px]">
                            {cause.gap}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {cause.studyTask}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Untimed Mode Summary */}
            {activeMode === "untimed" && (
              <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900/50 text-center">
                <span className="text-xs text-purple-700 dark:text-purple-300 font-bold uppercase tracking-wider block">
                  Session Score
                </span>
                <span className="text-3xl font-black text-gray-900 dark:text-white">
                  {untimedStats.correct} / {items.length} (
                  {items.length > 0
                    ? Math.round((untimedStats.correct / items.length) * 100)
                    : 0}
                  %)
                </span>
              </div>
            )}

            {/* Bottom Actions */}
            <div className="flex justify-center gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
              <button
                type="button"
                onClick={() => {
                  setCompleted(false);
                  setInProgress(false);
                }}
                className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
              >
                Take Another Drill / Test
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="px-5 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 rounded-xl text-xs font-semibold transition-all"
              >
                Return to Dashboard
              </button>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
