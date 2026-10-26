import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { weeklyTestApi, diagnosticApi } from "../api/client";

export default function AssessmentsHub() {
  const navigate = useNavigate();
  const [weeklyStatus, setWeeklyStatus] = useState(null);
  const [diagnosticStatus, setDiagnosticStatus] = useState(null);

  useEffect(() => {
    weeklyTestApi.getStatus().then(setWeeklyStatus).catch(() => null);
    diagnosticApi.getStatus().then(setDiagnosticStatus).catch(() => null);
  }, []);

  const getDiagnosticBadge = () => {
    if (diagnosticStatus?.is_completed) {
      return {
        badge: "Completed ✓ • Baseline Established",
        color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800",
        description: `Baseline established on ${diagnosticStatus.completed_at ? new Date(diagnosticStatus.completed_at).toLocaleDateString() : "recently"}. Score: ${Math.round(diagnosticStatus.score || 0)}% across 10 curriculum-stratified items.`,
        actionText: "Review Diagnostic",
        path: `/result/${diagnosticStatus.assessment_id}`,
        primary: false,
      };
    }
    if (diagnosticStatus?.status === "in_progress") {
      return {
        badge: "In Progress • Resumable",
        color: "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300",
        description: "Active diagnostic session in progress. Resume to calibrate your skill baseline.",
        actionText: "Resume Diagnostic",
        path: "/diagnostic",
        primary: true,
      };
    }
    return {
      badge: "Scored • Baseline",
      color: "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300",
      description: "Exactly 10 approved MCQs stratified across target skills in proportion to syllabus weights. Orders items from easy to hard with high-precision millisecond timing.",
      actionText: "Start Diagnostic",
      path: "/diagnostic/instructions",
      primary: true,
    };
  };

  const getWeeklyBadge = () => {
    if (!weeklyStatus || !weeklyStatus.is_scheduled) {
      return {
        badge: "Locked • Requires Diagnostic",
        color: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
        actionText: "Take Diagnostic First",
        path: "/diagnostic/instructions",
      };
    }
    if (weeklyStatus.status === "completed") {
      return {
        badge: "Completed ✓ • Cycle Done",
        color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300",
        actionText: "View Schedule",
        path: "/schedule",
      };
    }
    if (weeklyStatus.is_overdue) {
      return {
        badge: "Overdue • Day 7 Milestone",
        color: "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-800",
        actionText: "Take Weekly Test (Overdue)",
        path: "/weekly-test",
      };
    }
    if (weeklyStatus.is_due) {
      return {
        badge: "Due Today • Day 7 Milestone",
        color: "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-300 dark:border-purple-800",
        actionText: "Start Weekly Test",
        path: "/weekly-test",
      };
    }
    return {
      badge: `Not due yet • Due ${weeklyStatus.scheduled_date}`,
      color: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
      actionText: "Not Due Yet",
      path: "/weekly-test",
    };
  };

  const diagBadge = getDiagnosticBadge();
  const weeklyBadge = getWeeklyBadge();

  const assessmentModes = [
    {
      id: "diagnostic",
      title: "Initial Diagnostic Assessment",
      badge: diagBadge.badge,
      badgeColor: diagBadge.color,
      description: diagBadge.description,
      meta: "10 Questions • ~15 Mins • Baseline Calibrated",
      actionText: diagBadge.actionText,
      path: diagBadge.path,
      primary: diagBadge.primary,
    },
    {
      id: "weekly",
      title: "Weekly Progress Test (20 Qs)",
      badge: weeklyBadge.badge,
      badgeColor: weeklyBadge.color,
      description:
        "Comprehensive 20-item milestone: 10 questions from weekly priority topics, 5 root-cause prerequisite items, and 5 spaced reviews. Calibrates mastery and generates next week's schedule.",
      meta: "20 Questions • ~25 Mins • Scored Milestone",
      actionText: weeklyBadge.actionText,
      path: weeklyBadge.path,
      primary: Boolean(weeklyStatus?.is_due || weeklyStatus?.is_overdue),
    },
    {
      id: "special",
      title: "Special Timed Test Mode",
      badge: "High-Pressure • Diagnostic Probes",
      badgeColor: "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300",
      description:
        "Multi-block timed test: 30-second main questions followed immediately by 3 dynamic 20-second sub-questions biased toward prerequisite root causes. Features coral countdown ring and auto-submit timeouts.",
      meta: "5 Blocks (20 items) • Hard Time Limits • Auto-Submit",
      actionText: "Launch Special Test",
      path: "/special-test",
      primary: false,
    },
    {
      id: "verification",
      title: "Verification Probes",
      badge: "Root-Cause Validation",
      badgeColor: "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300",
      description:
        "Focused 2–3 question probes targeting suspected root-cause ancestors flagged by high GAT attention weights (Formula 8). Validates whether prerequisite gaps explain surface errors.",
      meta: "2–3 Probes • High Precision • ε-Random Mix",
      actionText: "Take Verification Probes",
      path: "/verification",
      primary: false,
    },
    {
      id: "followup",
      title: "Follow-Up Assessment",
      badge: "Research Trial • Post-Test",
      badgeColor: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300",
      description:
        "Evaluates retention and mastery gain after completing recommended remediation sequences. Measures RCT effect size and updates post-intervention status.",
      meta: "10 Questions • Effect Size Tracking • Scored",
      actionText: "Take Follow-Up Test",
      path: "/followup",
      primary: false,
    },
    {
      id: "practice",
      title: "Adaptive Practice Drills",
      badge: "Unscored • Free Drill",
      badgeColor: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300",
      description:
        "Low-stakes repetitive practice drills with immediate explanations after each answer. Zero penalty to formal diagnostic mastery scores.",
      meta: "Unlimited • Instant Worked Solutions",
      actionText: "Open Practice Drills",
      path: "/practice",
      primary: false,
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
            Assessments &amp; Testing Hub
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
            Choose from calibrated psychometric diagnostics, high-pressure timed probes, root-cause verification, or low-stakes adaptive practice.
          </p>
        </div>

        {/* Test Integrity Notice */}
        <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 flex items-start space-x-3">
          <span className="text-xl">🛡️</span>
          <div className="text-xs text-amber-900 dark:text-amber-200">
            <strong className="font-bold">Strict Psychometric Integrity Policy:</strong> For all scored assessments (Initial Diagnostic, Special Test, Verification Probes, and Follow-Up), the Gemini AI Assistant is strictly disabled to prevent answer leakage. Millisecond response timers capture authentic cognitive response patterns.
          </div>
        </div>

        {/* Assessment Modes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {assessmentModes.map((mode) => (
            <div
              key={mode.id}
              className={`p-6 sm:p-7 rounded-2xl border transition-all flex flex-col justify-between ${
                mode.primary
                  ? "bg-gradient-to-br from-purple-500/5 via-white to-rose-500/5 dark:from-purple-950/20 dark:via-gray-900 dark:to-rose-950/20 border-purple-200 dark:border-purple-800 shadow-md"
                  : "bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-800 shadow-sm hover:border-purple-200 dark:hover:border-purple-800"
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span
                    className={`px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${mode.badgeColor}`}
                  >
                    {mode.badge}
                  </span>
                  <span className="text-[11px] font-mono text-gray-400">
                    {mode.meta.split("•")[0]}
                  </span>
                </div>

                <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                  {mode.title}
                </h2>

                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {mode.description}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <span className="text-[11px] text-gray-400 font-medium">
                  {mode.meta}
                </span>

                <button
                  type="button"
                  onClick={() => navigate(mode.path)}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold shadow-sm transition-all ${
                    mode.primary
                      ? "bg-purple-600 hover:bg-purple-700 text-white shadow-purple-500/20"
                      : "bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white"
                  }`}
                >
                  {mode.actionText} →
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
