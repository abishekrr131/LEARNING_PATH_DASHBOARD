import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { analyticsApi } from "../api/client";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  LineChart,
  Line,
  ReferenceLine,
} from "recharts";

// Custom Tooltip for Domain-wise Mastery vs Syllabus Weight
function CustomDomainTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-gray-900/95 backdrop-blur border border-gray-700 p-3.5 rounded-xl shadow-2xl text-xs space-y-2 z-50 min-w-[240px]">
        <div className="border-b border-gray-800 pb-1.5">
          <p className="font-bold text-white text-sm">{data.fullName}</p>
          <p className="text-[11px] text-gray-400">Curriculum Domain Analysis</p>
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-purple-300">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-purple-500 inline-block" />
              Demonstrated Mastery:
            </span>
            <span className="font-black text-purple-400 text-sm">{data.mastery}%</span>
          </div>
          <div className="flex items-center justify-between text-sky-300">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-sky-400 inline-block" />
              Syllabus Weight:
            </span>
            <span className="font-bold text-sky-400">{data.weight}%</span>
          </div>
        </div>
        <div className="pt-1.5 border-t border-gray-800 flex items-center justify-between text-gray-300 text-[11px]">
          <span>Demonstrated Topics:</span>
          <span className="font-semibold text-gray-100">
            {data.demonstrated_topics} of {data.total_topics} topics
          </span>
        </div>
        <div className="pt-1 text-[10px]">
          {data.mastery >= data.weight ? (
            <span className="text-emerald-400 font-semibold">
              ✓ Demonstrating parity with syllabus weight
            </span>
          ) : (
            <span className="text-amber-300 font-medium">
              ⚠️ Mastery gap: {Math.max(0, data.weight - data.mastery)}% below syllabus weight
            </span>
          )}
        </div>
      </div>
    );
  }
  return null;
}

// Custom Tooltip for Assessment Progression Over Time
function CustomHistoryTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-gray-900/95 backdrop-blur border border-gray-700 p-3 rounded-xl shadow-2xl text-xs space-y-1.5 z-50 min-w-[200px]">
        <p className="font-bold text-white text-sm border-b border-gray-800 pb-1">{data.title}</p>
        <div className="flex items-center justify-between text-purple-300">
          <span>Score:</span>
          <span className="font-black text-purple-400 text-sm">{data.score}%</span>
        </div>
        <div className="flex items-center justify-between text-gray-300">
          <span>Accuracy:</span>
          <span>
            {data.correct} of {data.total} correct
          </span>
        </div>
        {data.completedAt && (
          <div className="text-[10px] text-gray-400 pt-1 border-t border-gray-800">
            {new Date(data.completedAt).toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        )}
      </div>
    );
  }
  return null;
}

export default function ProgressReadiness() {
  const [readiness, setReadiness] = useState(null);
  const [masteryData, setMasteryData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      analyticsApi.getReadiness(),
      analyticsApi.getMastery(),
      analyticsApi.getMistakeHistory().catch(() => ({ sessions: [] })),
    ])
      .then(([rData, mData, hData]) => {
        setReadiness(rData);
        setMasteryData(mData);
        setHistoryData(hData);
      })
      .catch((err) => setError(err.message || "Failed to load readiness details"))
      .finally(() => setLoading(false));
  }, []);

  // Format domain mastery chart data
  const domainChartData = useMemo(() => {
    if (!readiness?.skill_components) return [];
    return readiness.skill_components.map((skill) => {
      const weightPct = Math.round((skill.weight || 0) * 100);
      const masteryPct =
        skill.skill_percentage != null
          ? Number(skill.skill_percentage)
          : Math.round((skill.mean_mastery || 0) * 100);

      const fullName = skill.skill_name || "Domain";
      const displayName = fullName.length > 22 ? `${fullName.slice(0, 20)}…` : fullName;

      return {
        id: skill.skill_id,
        name: displayName,
        fullName: fullName,
        weight: weightPct,
        mastery: masteryPct,
        demonstrated_topics: skill.demonstrated_topics || 0,
        total_topics: skill.total_topics || skill.concept_count || 0,
        progress_text: skill.progress_text,
      };
    });
  }, [readiness]);

  // Format assessment progress over time data
  const historyChartData = useMemo(() => {
    if (!historyData?.sessions || historyData.sessions.length === 0) return [];
    // Sessions returned newest first, sort chronologically
    const sorted = [...historyData.sessions].sort((a, b) => {
      const da = a.completed_at ? new Date(a.completed_at).getTime() : 0;
      const db = b.completed_at ? new Date(b.completed_at).getTime() : 0;
      return da - db;
    });

    return sorted.map((s, idx) => {
      let dateLabel = s.short_label || `Test #${idx + 1}`;
      if (s.completed_at) {
        const d = new Date(s.completed_at);
        const day = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
        dateLabel = `${s.short_label || "Test"} (${day})`;
      }
      return {
        sessionId: s.assessment_id,
        label: dateLabel,
        title: s.title || s.short_label || "Assessment",
        score: s.score_pct != null ? s.score_pct : s.score || 0,
        correct: s.correct_count || 0,
        total: s.total_questions || 0,
        completedAt: s.completed_at,
        type: s.type,
      };
    });
  }, [historyData]);

  const thresholdPct = Math.round((readiness?.readiness_threshold || 0.7) * 100);
  const isAssessed = Boolean(readiness?.is_assessed);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
                Exam Readiness &amp; Progress Analytics
              </h1>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                estimate, not guarantee
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Coverage-weighted psychometric readiness index derived from Formula 17 across all curriculum skills.
            </p>
          </div>
        </div>

        {loading && (
          <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Calculating curriculum coverage and IRT parameters…</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
            {error}
          </div>
        )}

        {!loading && readiness && (
          <>
            {/* Top Readiness Score Card */}
            <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-br from-purple-900 via-indigo-900 to-gray-950 text-white shadow-xl relative overflow-hidden">
              <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 text-purple-200">
                      {readiness.target_name} Target
                    </span>
                    {readiness.learning_stage && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/80 text-white">
                        {readiness.learning_stage}
                      </span>
                    )}
                    <span className="text-xs text-rose-300 font-medium">
                      ({readiness.label || "Provisional estimate"})
                    </span>
                  </div>
                  <h2 className="text-4xl sm:text-5xl font-black tracking-tight text-white">
                    {isAssessed
                      ? readiness.topic_coverage_readiness_pct != null
                        ? `${readiness.topic_coverage_readiness_pct}%`
                        : `${readiness.readiness_percentage || 0}%`
                      : "Not assessed yet"}
                  </h2>
                  <div className="mt-2 text-xs sm:text-sm text-purple-200 max-w-md space-y-1">
                    <p>
                      <strong>Topic Coverage Readiness:</strong>{" "}
                      {readiness.demonstrated_topics_count || 0} of {readiness.total_syllabus_topics || 0} syllabus topics demonstrated correctly.
                    </p>
                    {readiness.is_ready ? (
                      <p className="text-emerald-400 font-semibold">
                        ✓ Readiness threshold achieved (Threshold: {thresholdPct}%). Continue spaced reviews to preserve retention.
                      </p>
                    ) : (
                      <p>
                        Target threshold is {thresholdPct}%. Gap to threshold:{" "}
                        <strong className="text-amber-300">
                          {isAssessed && readiness.topic_coverage_readiness_pct != null
                            ? `${Math.max(0, Math.round(thresholdPct - readiness.topic_coverage_readiness_pct))}%`
                            : "Take Diagnostic"}
                        </strong>
                      </p>
                    )}
                  </div>
                </div>

                {/* Progress bar container */}
                <div className="w-full md:w-72 bg-white/10 p-4 rounded-2xl border border-white/10 backdrop-blur-sm space-y-2">
                  <div className="flex justify-between text-xs text-purple-200">
                    <span>Current Score</span>
                    <span className="font-bold">
                      {isAssessed && readiness.readiness_score != null
                        ? `${readiness.readiness_score.toFixed(2)} / 1.00`
                        : "Not assessed"}
                    </span>
                  </div>
                  <div className="h-3 w-full bg-white/10 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-1000 ${
                        readiness.is_ready
                          ? "bg-gradient-to-r from-emerald-400 to-teal-400"
                          : "bg-gradient-to-r from-purple-400 via-indigo-400 to-rose-400"
                      }`}
                      style={{ width: `${Math.min(100, isAssessed ? (readiness.readiness_percentage || 0) : 0)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-purple-300/80">
                    <span>Baseline (0.00)</span>
                    <span>Threshold ({readiness.readiness_threshold})</span>
                    <span>Mastery (1.00)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Formula 17 Explanation Banner */}
            <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 text-xs text-gray-600 dark:text-gray-400 space-y-1">
              <span className="font-bold text-gray-900 dark:text-white block">
                Psychometric Readiness Formulation (Formula 17):
              </span>
              <p className="font-mono text-[11px] text-purple-700 dark:text-purple-300">
                {"R = \u2211(w_s \u00B7 m_s) where m_s = (1 / |C_s|) \u2211(m_c)"}
              </p>
              <p className="text-[11px] text-gray-500">
                Each skill $s$ contributes proportionally to syllabus weight $w_s \in (0, 1]$, and concept mastery $m_c$ is derived from calibrated IRT response modeling.
              </p>
            </div>

            {/* Unassessed Baseline Notice if user has not taken diagnostic */}
            {!isAssessed && (
              <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-purple-500/10 via-indigo-500/10 to-amber-500/10 border border-purple-300 dark:border-purple-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
                      Unassessed Baseline
                    </span>
                    <h4 className="font-bold text-sm text-gray-900 dark:text-white">
                      Curriculum Weights Displayed (Demonstrated Mastery: 0%)
                    </h4>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 max-w-2xl">
                    You have not yet completed the Initial Diagnostic for{" "}
                    <strong>{readiness.target_name}</strong>. The charts below contrast your target's
                    official syllabus weights against your current measured baseline. Take the diagnostic to calibrate your skill mastery.
                  </p>
                </div>
                <Link
                  to="/diagnostic"
                  className="shrink-0 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold shadow-md transition-all"
                >
                  Take Initial Diagnostic →
                </Link>
              </div>
            )}

            {/* GRAPHS SECTION */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Graph 1: Domain-wise Skill Mastery vs Syllabus Weight */}
              <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-bold text-base text-gray-900 dark:text-white">
                      Domain Mastery vs. Syllabus Weight
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300">
                      {domainChartData.length} Domains
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-6">
                    Compares your demonstrated mastery against the syllabus weight for each domain in{" "}
                    <strong>{readiness.target_name}</strong>.
                  </p>

                  <div style={{ height: Math.max(260, domainChartData.length * 62) }} className="w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        layout="vertical"
                        data={domainChartData}
                        margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#374151" opacity={0.25} />
                        <XAxis
                          type="number"
                          domain={[0, 100]}
                          unit="%"
                          tick={{ fill: "#9ca3af", fontSize: 11 }}
                          axisLine={{ stroke: "#4b5563" }}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={140}
                          tick={{ fill: "#9ca3af", fontSize: 11 }}
                          axisLine={{ stroke: "#4b5563" }}
                        />
                        <Tooltip content={<CustomDomainTooltip />} />
                        <Legend
                          verticalAlign="top"
                          align="right"
                          iconType="circle"
                          wrapperStyle={{ paddingBottom: 12, fontSize: 12 }}
                        />
                        <Bar
                          dataKey="mastery"
                          name="Demonstrated Mastery %"
                          fill="#9333ea"
                          radius={[0, 6, 6, 0]}
                          barSize={14}
                        />
                        <Bar
                          dataKey="weight"
                          name="Syllabus Weight %"
                          fill="#38bdf8"
                          radius={[0, 6, 6, 0]}
                          barSize={14}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
                  <span>🟣 Mastery reflects validated correct responses</span>
                  <span>🔵 Weight reflects curriculum distribution</span>
                </div>
              </div>

              {/* Graph 2: Progress Over Time */}
              <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-bold text-base text-gray-900 dark:text-white">
                      Assessment Performance Progression
                    </h3>
                    {historyChartData.length > 0 && (
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                        {historyChartData.length} Evaluations Recorded
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-6">
                    Track your calibrated assessment scores over time relative to the target threshold ({thresholdPct}%).
                  </p>

                  {historyChartData.length > 0 ? (
                    <div style={{ height: Math.max(260, domainChartData.length * 62) }} className="w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={historyChartData}
                          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.25} />
                          <XAxis
                            dataKey="label"
                            tick={{ fill: "#9ca3af", fontSize: 11 }}
                            axisLine={{ stroke: "#4b5563" }}
                          />
                          <YAxis
                            domain={[0, 100]}
                            unit="%"
                            tick={{ fill: "#9ca3af", fontSize: 11 }}
                            axisLine={{ stroke: "#4b5563" }}
                          />
                          <Tooltip content={<CustomHistoryTooltip />} />
                          <Legend
                            verticalAlign="top"
                            align="right"
                            iconType="circle"
                            wrapperStyle={{ paddingBottom: 12, fontSize: 12 }}
                          />
                          <ReferenceLine
                            y={thresholdPct}
                            stroke="#10b981"
                            strokeDasharray="4 4"
                            strokeWidth={1.5}
                            label={{
                              value: `Threshold (${thresholdPct}%)`,
                              fill: "#10b981",
                              fontSize: 10,
                              position: "insideTopRight",
                            }}
                          />
                          <Line
                            type="monotone"
                            dataKey="score"
                            name="Evaluation Score %"
                            stroke="#9333ea"
                            strokeWidth={3}
                            dot={{ r: 5, fill: "#9333ea", stroke: "#c084fc", strokeWidth: 2 }}
                            activeDot={{ r: 7 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div
                      style={{ height: Math.max(260, domainChartData.length * 62) }}
                      className="w-full flex flex-col items-center justify-center p-6 text-center rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-dashed border-gray-200 dark:border-gray-800 space-y-3"
                    >
                      <div className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center text-xl">
                        📈
                      </div>
                      <div className="space-y-1">
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">
                          No Assessment History Yet
                        </h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400 max-w-sm">
                          Complete your Initial Diagnostic or weekly evaluation to start tracking your genuine test score progression over time.
                        </p>
                      </div>
                      <Link
                        to="/diagnostic"
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                      >
                        Start Initial Diagnostic
                      </Link>
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
                  <span>Threshold: {thresholdPct}% readiness standard</span>
                  <span>{historyChartData.length} evaluation(s)</span>
                </div>
              </div>
            </div>

            {/* Skill Components Breakdown Table */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-base text-gray-900 dark:text-white">
                    Detailed Curriculum Domains
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Breakdown of topics demonstrated vs total syllabus requirements
                  </p>
                </div>
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                  {readiness.skill_components.length} Curriculum Domains
                </span>
              </div>

              <div className="divide-y divide-gray-100 dark:divide-gray-800">
                {readiness.skill_components.map((skill) => (
                  <div
                    key={skill.skill_id}
                    className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">
                          {skill.skill_name}
                        </h4>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300">
                          Weight: {Math.round(skill.weight * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {skill.progress_text || `${skill.demonstrated_topics || 0} of ${skill.total_topics || skill.concept_count || 0} topics demonstrated`}
                      </p>
                    </div>

                    <div className="flex items-center space-x-6">
                      <div className="w-40 sm:w-48">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">Domain Mastery</span>
                          <span className="font-bold text-gray-900 dark:text-white">
                            {skill.skill_percentage != null ? `${skill.skill_percentage}%` : `${Math.round((skill.mean_mastery || 0) * 100)}%`}
                          </span>
                        </div>
                        <div className="h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="bg-purple-600 h-full rounded-full transition-all duration-700"
                            style={{ width: `${skill.skill_percentage != null ? skill.skill_percentage : (skill.mean_mastery || 0) * 100}%` }}
                          />
                        </div>
                      </div>

                      <span
                        className={`text-xs font-bold px-2.5 py-1 rounded-lg ${
                          skill.mean_mastery >= 0.70
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                            : skill.mean_mastery >= 0.40
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                            : "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                        }`}
                      >
                        {skill.mean_mastery >= 0.70 ? "Strong" : skill.mean_mastery >= 0.40 ? "Moderate" : "Weak"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-between p-6 rounded-2xl bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/40 gap-4">
              <div>
                <h4 className="font-bold text-purple-950 dark:text-purple-200 text-sm">
                  Ready to improve your readiness score?
                </h4>
                <p className="text-xs text-purple-800/80 dark:text-purple-300/80 mt-0.5">
                  Complete targeted remediation exercises on weak concepts or take a follow-up assessment.
                </p>
              </div>

              <div className="flex items-center space-x-3 w-full sm:w-auto">
                <Link
                  to="/weak-topics"
                  className="px-4 py-2 border border-purple-300 dark:border-purple-800 text-purple-700 dark:text-purple-300 rounded-xl text-xs font-semibold hover:bg-white dark:hover:bg-gray-800 transition-colors text-center w-full sm:w-auto"
                >
                  Inspect Weak Topics
                </Link>
                <Link
                  to="/followup"
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors text-center w-full sm:w-auto"
                >
                  Take Follow-Up Test
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}
