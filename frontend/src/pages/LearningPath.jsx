import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { learningApi } from "../api/client";

export default function LearningPath() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [careerMap, setCareerMap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("career-map"); // 'career-map' | 'dag-path'
  const [filter, setFilter] = useState("all"); // 'all', 'remediation', 'ready', 'mastered'
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      learningApi.getPath().catch(() => null),
      learningApi.getCareerMap().catch(() => null),
    ])
      .then(([pathData, mapData]) => {
        setData(pathData);
        setCareerMap(mapData);
        if (pathData?.path?.length > 0) {
          setSelectedNode(pathData.path[0]);
        }
      })
      .catch((err) => setError(err.message || "Failed to load learning path"))
      .finally(() => setLoading(false));
  }, []);

  const path = data?.path || [];
  const filteredPath = path.filter((node) => {
    if (filter === "remediation") return node.is_remediation_inserted;
    if (filter === "ready") return node.status === "ready_to_learn";
    if (filter === "mastered") return node.status === "mastered";
    return true;
  });

  const getStatusBadge = (status, isRemediation) => {
    if (isRemediation) {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800 animate-pulse">
          ⚡ Remediation Inserted
        </span>
      );
    }
    switch (status) {
      case "mastered":
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
            ✓ Mastered
          </span>
        );
      case "ready_to_learn":
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300">
            🎯 Ready to Learn
          </span>
        );
      case "locked":
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
            🔒 Prerequisite Locked
          </span>
        );
    }
  };

  const getStageBadge = (stage) => {
    switch (stage) {
      case "Career Ready":
        return "bg-emerald-500 text-white";
      case "Proficient Stage":
        return "bg-indigo-600 text-white";
      case "Developing Stage":
        return "bg-purple-600 text-white";
      case "Foundation Stage":
        return "bg-amber-500 text-white";
      default:
        return "bg-gray-600 text-white";
    }
  };

  return (
    <MainLayout currentConcept={selectedNode ? { id: selectedNode.concept_id, name: selectedNode.concept_name } : null}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
                Adaptive Career Ready Map
              </h1>
              {careerMap?.learning_stage && (
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${getStageBadge(careerMap.learning_stage)}`}>
                  {careerMap.learning_stage}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Real-time curriculum coverage, demonstrated mastery, root-cause prerequisite gaps, and sequential unlocks for {careerMap?.target_name || "your target career"}.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => navigate("/practice")}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-500/20"
            >
              Start Adaptive Practice
            </button>
            <button
              onClick={() => navigate("/resources")}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-300 text-gray-700 dark:text-gray-200 rounded-xl text-xs font-semibold shadow-sm"
            >
              Study Materials ↗
            </button>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-800">
          <button
            onClick={() => setActiveTab("career-map")}
            className={`pb-3 px-4 text-xs font-bold border-b-2 transition-all ${
              activeTab === "career-map"
                ? "border-purple-600 text-purple-600 dark:text-purple-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            }`}
          >
            🗺️ Career Ready Map (Overview)
          </button>
          <button
            onClick={() => setActiveTab("dag-path")}
            className={`pb-3 px-4 text-xs font-bold border-b-2 transition-all ${
              activeTab === "dag-path"
                ? "border-purple-600 text-purple-600 dark:text-purple-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            }`}
          >
            🌿 Topological DAG Curriculum Path
          </button>
        </div>

        {loading && (
          <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Computing topic coverage readiness and DAG prerequisites…</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 1: CAREER READY MAP (OVERVIEW) */}
        {/* ============================================================== */}
        {!loading && !error && activeTab === "career-map" && careerMap && (
          <div className="space-y-6">
            {/* Top Readiness Hero Card */}
            <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-br from-purple-900 via-indigo-950 to-gray-950 text-white shadow-xl relative overflow-hidden">
              <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 text-purple-200">
                      {careerMap.target_name}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${getStageBadge(careerMap.learning_stage)}`}>
                      {careerMap.learning_stage}
                    </span>
                  </div>
                  <h2 className="text-4xl sm:text-5xl font-black tracking-tight text-white">
                    {careerMap.topic_coverage_readiness_pct}%
                  </h2>
                  <p className="text-xs sm:text-sm text-purple-200 mt-2 max-w-xl leading-relaxed">
                    <strong>Topic Coverage Readiness:</strong> Demonstrated {careerMap.demonstrated_topics_count} of {careerMap.total_syllabus_topics} syllabus topics correctly.
                    {careerMap.total_attempts > 0 && (
                      <span className="block mt-1 text-purple-300">
                        Raw Test Accuracy: <strong>{careerMap.raw_accuracy_pct}%</strong> ({careerMap.correct_count} of {careerMap.total_attempts} questions correct). Distinct from topic coverage.
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-purple-300/80 mt-2">
                    {careerMap.stage_description}
                  </p>
                </div>

                {/* Progress Gauge */}
                <div className="w-full md:w-80 bg-white/10 p-5 rounded-2xl border border-white/10 backdrop-blur-sm space-y-3">
                  <div className="flex justify-between text-xs text-purple-200">
                    <span>Topic Coverage</span>
                    <span className="font-bold">{careerMap.demonstrated_topics_count} / {careerMap.total_syllabus_topics} Topics</span>
                  </div>
                  <div className="h-3.5 w-full bg-white/10 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-1000 ${
                        careerMap.is_career_ready
                          ? "bg-gradient-to-r from-emerald-400 to-teal-400"
                          : "bg-gradient-to-r from-purple-400 via-indigo-400 to-rose-400"
                      }`}
                      style={{ width: `${Math.min(100, careerMap.topic_coverage_readiness_pct)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-purple-300/80">
                    <span>Foundation (0%)</span>
                    <span>Target ({careerMap.readiness_threshold_pct}%)</span>
                    <span>Ready (100%)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Next Topic to Unlock Card */}
            {careerMap.next_unlocked_topic && (
              <div className="p-5 rounded-2xl bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/40 dark:to-purple-950/40 border border-indigo-200 dark:border-indigo-900/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-600 text-white flex items-center justify-center text-lg font-bold shrink-0">
                    🔓
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-purple-700 dark:text-purple-300 uppercase tracking-wider block">
                      Next Topic to Unlock
                    </span>
                    <h3 className="font-bold text-gray-900 dark:text-white text-base">
                      {careerMap.next_unlocked_topic.topic_name}
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {careerMap.next_unlocked_topic.skill_name} · {careerMap.next_unlocked_topic.reason}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={() => navigate(`/practice?topic_id=${careerMap.next_unlocked_topic.topic_id}`)}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                  >
                    Start Topic Practice
                  </button>
                  <button
                    onClick={() => navigate("/resources")}
                    className="px-3.5 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-300 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold"
                  >
                    Study Materials ↗
                  </button>
                </div>
              </div>
            )}

            {/* Progress Milestones Checklist */}
            {careerMap.milestones && (
              <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4">
                <h3 className="font-bold text-base text-gray-900 dark:text-white flex items-center justify-between">
                  <span>Milestones Toward 100% Readiness</span>
                  <span className="text-xs text-gray-400 font-normal">
                    {careerMap.milestones.filter((m) => m.completed).length} of {careerMap.milestones.length} Completed
                  </span>
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {careerMap.milestones.map((m) => (
                    <div
                      key={m.id}
                      className={`p-4 rounded-xl border flex flex-col justify-between space-y-2 transition-all ${
                        m.completed
                          ? "bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/60"
                          : "bg-gray-50/50 dark:bg-gray-800/40 border-gray-100 dark:border-gray-800"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <span className="font-bold text-xs text-gray-900 dark:text-white">
                          {m.title}
                        </span>
                        {m.completed ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                            ✓ Done
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                            {m.progress_pct}%
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-snug">
                        {m.description}
                      </p>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 h-1.5 rounded-full overflow-hidden mt-1">
                        <div
                          className={`h-full ${m.completed ? "bg-emerald-500" : "bg-purple-600"}`}
                          style={{ width: `${m.progress_pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3 Core Buckets: Demonstrated / Weak Topics & Gaps / Unassessed */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* 1. Demonstrated Topics */}
              <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                      Demonstrated Topics
                    </h3>
                  </div>
                  <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                    {careerMap.demonstrated_topics?.length || 0}
                  </span>
                </div>
                <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-1">
                  {careerMap.demonstrated_topics?.map((top) => (
                    <div
                      key={top.topic_id}
                      className="p-3 rounded-xl bg-emerald-50/40 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 flex items-center justify-between"
                    >
                      <div>
                        <h4 className="font-semibold text-xs text-gray-900 dark:text-white">
                          {top.topic_name}
                        </h4>
                        <span className="text-[10px] text-gray-400">{top.skill_name}</span>
                      </div>
                      <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950/60 px-2 py-0.5 rounded">
                        ✓ Mastered
                      </span>
                    </div>
                  ))}
                  {(!careerMap.demonstrated_topics || careerMap.demonstrated_topics.length === 0) && (
                    <p className="text-xs text-gray-400 p-4 text-center">
                      No topics demonstrated yet. Take the diagnostic to establish proven topics.
                    </p>
                  )}
                </div>
              </div>

              {/* 2. Weak Topics & Prerequisite Gaps */}
              <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-rose-100 dark:border-rose-950/40 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
                    <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                      Weak Topics &amp; DAG Gaps
                    </h3>
                  </div>
                  <span className="text-xs font-bold text-rose-600 dark:text-rose-400">
                    {careerMap.weak_topics?.length || 0}
                  </span>
                </div>
                <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                  {careerMap.weak_topics?.map((top) => (
                    <div
                      key={top.topic_id}
                      className="p-3.5 rounded-xl bg-rose-50/40 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/60 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-bold text-xs text-gray-900 dark:text-white">
                            {top.topic_name}
                          </h4>
                          <span className="text-[10px] text-gray-400">{top.skill_name}</span>
                        </div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          top.priority === "HIGH"
                            ? "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
                            : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                        }`}>
                          {top.priority} Priority
                        </span>
                      </div>
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={() => navigate(top.practice_url)}
                          className="text-[11px] font-semibold text-purple-600 dark:text-purple-400 hover:underline"
                        >
                          Targeted Practice →
                        </button>
                        <button
                          onClick={() => navigate("/resources")}
                          className="text-[11px] font-semibold text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                        >
                          Study Resources ↗
                        </button>
                      </div>
                    </div>
                  ))}
                  {(!careerMap.weak_topics || careerMap.weak_topics.length === 0) && (
                    <p className="text-xs text-gray-400 p-4 text-center">
                      No weak topic gaps identified!
                    </p>
                  )}
                </div>
              </div>

              {/* 3. Unassessed Topics (Flagged for Follow-Up) */}
              <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                    <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                      Unassessed (Needs Follow-Up)
                    </h3>
                  </div>
                  <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
                    {careerMap.unassessed_topics?.length || 0}
                  </span>
                </div>
                <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-1">
                  {careerMap.unassessed_topics?.map((top) => (
                    <div
                      key={top.topic_id}
                      className="p-3 rounded-xl bg-indigo-50/40 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/40 flex items-center justify-between"
                    >
                      <div>
                        <h4 className="font-semibold text-xs text-gray-900 dark:text-white">
                          {top.topic_name}
                        </h4>
                        <span className="text-[10px] text-gray-400">{top.skill_name}</span>
                      </div>
                      <button
                        onClick={() => navigate(top.followup_url)}
                        className="text-[10px] font-bold text-indigo-700 dark:text-indigo-300 bg-indigo-100 dark:bg-indigo-950/60 px-2 py-1 rounded hover:bg-indigo-200 transition-colors"
                      >
                        Assess Topic →
                      </button>
                    </div>
                  ))}
                  {(!careerMap.unassessed_topics || careerMap.unassessed_topics.length === 0) && (
                    <p className="text-xs text-gray-400 p-4 text-center">
                      All syllabus topics assessed!
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Prerequisite Root Causes Banner */}
            {careerMap.prerequisite_gaps && careerMap.prerequisite_gaps.length > 0 && (
              <div className="p-6 bg-amber-50/60 dark:bg-amber-950/20 rounded-2xl border border-amber-200 dark:border-amber-900/60 space-y-3">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">⛓️</span>
                  <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                    DAG Prerequisite Root Causes Blocking Progress
                  </h3>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                  These upstream foundational prerequisites must be mastered before dependent concepts unlock smoothly.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  {careerMap.prerequisite_gaps.slice(0, 6).map((gap, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-white dark:bg-gray-900 border border-amber-200 dark:border-amber-900/60 flex items-center justify-between text-xs"
                    >
                      <div>
                        <strong className="text-gray-900 dark:text-white block font-semibold">
                          {gap.prerequisite_name}
                        </strong>
                        <span className="text-[10px] text-amber-700 dark:text-amber-400">
                          Blocks: {gap.blocks_concept_name}
                        </span>
                      </div>
                      <a
                        href={gap.resource_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] font-bold text-purple-600 dark:text-purple-400 hover:underline shrink-0 ml-3"
                      >
                        Study Prerequisite ↗
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 2: TOPOLOGICAL CURRICULUM PATH (DAG) */}
        {/* ============================================================== */}
        {!loading && !error && activeTab === "dag-path" && (
          <div className="space-y-6">
            {/* Stats Strip */}
            {data && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-sm">
                  <span className="text-xs text-gray-400 block font-medium">Total Concepts</span>
                  <span className="text-2xl font-black text-gray-900 dark:text-white mt-1">
                    {data.total_nodes}
                  </span>
                </div>
                <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-sm">
                  <span className="text-xs text-gray-400 block font-medium">Completed</span>
                  <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
                    {data.completed_count}
                  </span>
                </div>
                <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-sm">
                  <span className="text-xs text-gray-400 block font-medium">Remaining</span>
                  <span className="text-2xl font-black text-purple-600 dark:text-purple-400 mt-1">
                    {Math.max(0, data.total_nodes - data.completed_count)}
                  </span>
                </div>
                <div className="p-4 rounded-2xl bg-white dark:bg-gray-900 border border-amber-200 dark:border-amber-900/40 shadow-sm bg-gradient-to-br from-amber-500/5 to-transparent">
                  <span className="text-xs text-amber-600 dark:text-amber-400 block font-medium">
                    Active Remediations
                  </span>
                  <span className="text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">
                    {data.remediations_active || 0}
                  </span>
                </div>
              </div>
            )}

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 dark:border-gray-800 pb-3">
              <span className="text-xs font-semibold text-gray-500 mr-2">Filter View:</span>
              {[
                { id: "all", label: "All Nodes" },
                { id: "ready", label: "Ready to Learn" },
                { id: "remediation", label: "Remediations Only" },
                { id: "mastered", label: "Mastered" },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    filter === f.id
                      ? "bg-purple-600 text-white shadow-sm"
                      : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Pipeline & Details Split View */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left 2 Cols: Pipeline Nodes */}
              <div className="lg:col-span-2 space-y-3">
                {filteredPath.map((node, index) => {
                  const isSelected = selectedNode?.concept_id === node.concept_id;
                  return (
                    <div
                      key={node.concept_id}
                      onClick={() => setSelectedNode(node)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer relative ${
                        isSelected
                          ? "border-purple-500 bg-purple-50/50 dark:bg-purple-950/20 shadow-md"
                          : "border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-purple-200 dark:hover:border-purple-800"
                      } ${node.is_remediation_inserted ? "border-l-4 border-l-amber-500" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start space-x-3">
                          <div
                            className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${
                              node.status === "mastered"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : node.is_remediation_inserted
                                ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                                : "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300"
                            }`}
                          >
                            {index + 1}
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <h3 className="font-bold text-gray-900 dark:text-white text-sm">
                                {node.concept_name}
                              </h3>
                              {getStatusBadge(node.status, node.is_remediation_inserted)}
                            </div>
                            <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                              <span>{node.skill_name}</span>
                              <span>•</span>
                              <span>{node.topic_name}</span>
                              <span>•</span>
                              <span className="capitalize">{node.difficulty_level || "Standard"}</span>
                            </div>
                            {node.is_remediation_inserted && (
                              <p className="text-xs text-amber-700 dark:text-amber-400 font-medium mt-2 bg-amber-50 dark:bg-amber-950/40 p-2 rounded-lg border border-amber-200 dark:border-amber-900">
                                ⚠️ Remediation: {node.remediation_reason}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="text-right">
                          <span className="text-xs text-gray-400 block font-mono">
                            ID: #{node.concept_id}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {filteredPath.length === 0 && (
                  <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 text-gray-500">
                    No concepts match the selected filter.
                  </div>
                )}
              </div>

              {/* Right 1 Col: Selected Node Detail Drawer */}
              <div className="space-y-4">
                {selectedNode ? (
                  <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm sticky top-24 space-y-5">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">
                          Concept Details
                        </span>
                        {getStatusBadge(selectedNode.status, selectedNode.is_remediation_inserted)}
                      </div>
                      <h2 className="text-lg font-black text-gray-900 dark:text-white">
                        {selectedNode.concept_name}
                      </h2>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {selectedNode.skill_name} &gt; {selectedNode.topic_name}
                      </p>
                    </div>

                    <div className="space-y-3 border-t border-b border-gray-100 dark:border-gray-800 py-4 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Difficulty:</span>
                        <span className="font-semibold capitalize text-gray-900 dark:text-white">
                          {selectedNode.difficulty_level || "Standard"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Sequence Order:</span>
                        <span className="font-semibold font-mono text-gray-900 dark:text-white">
                          Node #{selectedNode.order_index || selectedNode.sequence_index}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2 pt-2">
                      <button
                        onClick={() => navigate(`/practice?concept_id=${selectedNode.concept_id}`)}
                        className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors text-center block"
                      >
                        Practice Questions for this Concept
                      </button>
                      <button
                        onClick={() => navigate(`/resources?concept_id=${selectedNode.concept_id}`)}
                        className="w-full py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold transition-colors text-center block"
                      >
                        View Curated Learning Materials
                      </button>
                      <Link
                        to={`/root-cause?concept_id=${selectedNode.concept_id}`}
                        className="w-full py-2 border border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300 rounded-xl text-xs font-medium hover:bg-purple-50 dark:hover:bg-purple-950/40 transition-colors text-center block"
                      >
                        Inspect Root Cause Tree
                      </Link>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 text-center text-gray-400 text-xs">
                    Select a concept to inspect its prerequisites and targeted actions.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
