import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { learningApi } from "../api/client";

export default function LearningPath() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all"); // 'all', 'remediation', 'ready', 'mastered'
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    learningApi
      .getPath()
      .then((res) => {
        setData(res);
        if (res?.path?.length > 0) {
          setSelectedNode(res.path[0]);
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

  return (
    <MainLayout currentConcept={selectedNode ? { id: selectedNode.concept_id, name: selectedNode.concept_name } : null}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
              Adaptive Curriculum Path (DAG)
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Topologically sorted concept progression with dynamically inserted prerequisite remediations from RCT-GAT attention routing.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => navigate("/practice")}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-500/20"
            >
              Start Adaptive Practice
            </button>
          </div>
        </div>

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
                {data.remediations_active}
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

        {/* Loading / Error States */}
        {loading && (
          <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Computing topological DAG sequence…</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Pipeline & Details Split View */}
        {!loading && !error && (
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
                            <span className="capitalize">{node.difficulty_level}</span>
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
                        {selectedNode.difficulty_level}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Sequence Order:</span>
                      <span className="font-semibold font-mono text-gray-900 dark:text-white">
                        Node #{selectedNode.order_index}
                      </span>
                    </div>
                    {selectedNode.unmet_prerequisites && selectedNode.unmet_prerequisites.length > 0 && (
                      <div>
                        <span className="text-gray-500 block mb-1">Unmet Prerequisites:</span>
                        <div className="flex flex-wrap gap-1">
                          {selectedNode.unmet_prerequisites.map((pId) => (
                            <span
                              key={pId}
                              className="px-2 py-0.5 rounded bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 font-mono text-[10px]"
                            >
                              Concept #{pId}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {selectedNode.is_remediation_inserted && (
                    <div className="p-3 bg-amber-50 dark:bg-amber-950/40 rounded-xl border border-amber-200 dark:border-amber-900 text-xs text-amber-800 dark:text-amber-300">
                      <strong>RCT-GAT Attention Prioritization:</strong> This concept was inserted ahead of dependent goals because diagnostics indicated an upstream prerequisite vulnerability.
                    </div>
                  )}

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
        )}
      </div>
    </MainLayout>
  );
}
