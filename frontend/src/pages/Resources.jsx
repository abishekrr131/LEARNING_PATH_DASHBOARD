import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { learningApi } from "../api/client";

export default function Resources() {
  const [searchParams] = useSearchParams();
  const conceptIdParam = searchParams.get("concept_id");

  const [resources, setResources] = useState([]);
  const [targetName, setTargetName] = useState("");
  const [contentGaps, setContentGaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [typeFilter, setTypeFilter] = useState("all");

  const loadResources = useCallback(() => {
    setLoading(true);
    setError(null);
    learningApi
      .getResources(conceptIdParam ? parseInt(conceptIdParam, 10) : null)
      .then((data) => {
        setResources(data.resources || []);
        setTargetName(data.target_name || "");
        setContentGaps(data.content_gaps || []);
      })
      .catch((err) => setError(err.message || "Failed to load curated resources."))
      .finally(() => setLoading(false));
  }, [conceptIdParam]);

  useEffect(() => {
    loadResources();
  }, [loadResources]);

  const filteredResources = resources.filter((r) => {
    if (typeFilter === "all") return true;
    if (typeFilter === "weak") return Boolean(r.is_weak_topic);
    if (typeFilter === "video") return r.resource_type?.toLowerCase() === "video";
    if (typeFilter === "doc") {
      const t = r.resource_type?.toLowerCase();
      return t === "documentation" || t === "textbook" || t === "article";
    }
    if (typeFilter === "interactive") {
      const t = r.resource_type?.toLowerCase();
      return t === "interactive" || t === "practice";
    }
    return r.resource_type?.toLowerCase() === typeFilter.toLowerCase();
  });

  const filterTabs = [
    { key: "all", label: "All Study Materials" },
    { key: "weak", label: "My Weak Topics" },
    { key: "doc", label: "Docs & Textbooks" },
    { key: "video", label: "Video Tutorials" },
    { key: "interactive", label: "Interactive & Practice" },
  ];

  const getTypeBadge = (type) => {
    const t = (type || "").toLowerCase();
    if (t === "video") return { icon: "🎬", label: "Video", bg: "bg-red-50 text-red-700 dark:bg-red-950/60 dark:text-red-300 border-red-200 dark:border-red-900" };
    if (t === "textbook") return { icon: "📖", label: "Textbook", bg: "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900" };
    if (t === "documentation") return { icon: "📑", label: "Documentation", bg: "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-900" };
    if (t === "interactive") return { icon: "💻", label: "Interactive", bg: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900" };
    if (t === "practice") return { icon: "✍️", label: "Practice Drill", bg: "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-900" };
    return { icon: "📄", label: "Curated Notes", bg: "bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-900" };
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
                Online Study Materials &amp; Resources
              </h1>
              {targetName && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-300">
                  {targetName}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Authoritative, verified online learning materials from official exam bodies (IBPS, UPSC, SSC, SATHEE, NCERT, NPTEL) and tech documentation (MDN, Python, React, PyTorch, OWASP) mapped to your syllabus and weak concepts.
            </p>
            {conceptIdParam && (
              <div className="mt-2 inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">
                Filtered for Concept #{conceptIdParam}
              </div>
            )}
          </div>
          <div className="shrink-0 flex items-center space-x-2">
            <button
              onClick={loadResources}
              disabled={loading}
              className="px-3.5 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 transition-all shadow-sm"
            >
              🔄 Refresh Materials
            </button>
          </div>
        </div>

        {/* Content Gap Alert if any */}
        {contentGaps.length > 0 && (
          <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-200">
            <strong>Notice on Content Availability:</strong> {contentGaps.length} syllabus topics currently lack direct verified online links and are actively being updated.
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-2">
          {filterTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTypeFilter(tab.key)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                typeFilter === tab.key
                  ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                  : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
              }`}
            >
              {tab.label}
              {tab.key === "weak" && (
                <span className="ml-1.5 px-1.5 py-0.2 rounded-full text-[10px] bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 font-bold">
                  {resources.filter((r) => r.is_weak_topic).length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="p-16 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm">
            <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h3 className="font-bold text-gray-900 dark:text-white">Retrieving Verified Online Materials…</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Matching curriculum syllabus against official textbooks, interactive guides, and diagnostic remediations.
            </p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-2xl border border-rose-200 dark:border-rose-900 shadow-sm space-y-4">
            <div className="text-3xl">⚠️</div>
            <h3 className="font-bold text-gray-900 dark:text-white">Failed to Load Resources</h3>
            <p className="text-xs text-rose-600 dark:text-rose-400 max-w-md mx-auto">{error}</p>
            <div className="flex justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={loadResources}
                className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Resource Cards Grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredResources.map((res) => {
              const typeBadge = getTypeBadge(res.resource_type);
              return (
                <div
                  key={res.id}
                  className={`p-6 bg-white dark:bg-gray-900 rounded-2xl border shadow-sm flex flex-col justify-between transition-all hover:shadow-md ${
                    res.is_weak_topic
                      ? "border-rose-200 dark:border-rose-900/60 hover:border-rose-400"
                      : "border-gray-100 dark:border-gray-800 hover:border-purple-200 dark:hover:border-purple-800"
                  }`}
                >
                  <div>
                    {/* Badges strip */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className={`px-2.5 py-0.5 rounded text-[11px] font-semibold border ${typeBadge.bg}`}>
                          {typeBadge.icon} {typeBadge.label}
                        </span>
                        {res.is_weak_topic && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-900">
                            ⚠️ Weak Topic
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                          ⏱️ {res.estimated_duration_min || 30} mins
                        </span>
                      </div>
                      <span className="text-[11px] font-medium text-purple-600 dark:text-purple-400 capitalize">
                        {res.difficulty || res.difficulty_level || "Intermediate"}
                      </span>
                    </div>

                    {(() => {
                      const url = res.url || "";
                      const isInternal =
                        res.is_internal ||
                        !url ||
                        url.includes("learn.internal") ||
                        url.startsWith("/") ||
                        url.startsWith("internal:");

                      if (isInternal && (res.id || res.concept_id)) {
                        return (
                          <Link
                            to={`/resources/${res.id || res.concept_id}`}
                            className="font-bold text-gray-900 dark:text-white text-base line-clamp-2 leading-snug hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
                          >
                            {res.title}
                          </Link>
                        );
                      }

                      return (
                        <h3 className="font-bold text-gray-900 dark:text-white text-base line-clamp-2 leading-snug">
                          {res.title}
                        </h3>
                      );
                    })()}

                    <div className="flex items-center space-x-1.5 text-xs text-purple-600 dark:text-purple-400 font-medium mt-1.5">
                      <span>{res.topic_name || "Topic"}</span>
                      <span>·</span>
                      <span className="text-gray-500 dark:text-gray-400">{res.concept_name}</span>
                    </div>

                    <p className="text-xs text-gray-600 dark:text-gray-300 mt-2.5 line-clamp-3 leading-relaxed">
                      {res.description}
                    </p>

                    <div className="mt-3.5 p-3 rounded-xl bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/40">
                      <span className="text-[10px] font-bold text-purple-700 dark:text-purple-300 uppercase tracking-wider block">
                        Why Recommended
                      </span>
                      <p className="text-xs text-purple-900 dark:text-purple-200 mt-0.5 leading-snug">
                        {res.why_recommended}
                      </p>
                    </div>

                    {/* Attribution / Provider */}
                    <div className="mt-3 text-[11px] text-gray-500 dark:text-gray-400 space-y-0.5">
                      <div><strong>Provider:</strong> {res.provider || res.source || "Official"}</div>
                      {res.license && <div><strong>License:</strong> {res.license}</div>}
                    </div>
                  </div>

                  <div className="mt-5 pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
                    <span className="text-[11px] text-gray-400 font-medium truncate max-w-[150px]">
                      {res.provider || "Verified Source"}
                    </span>
                    {(() => {
                      const url = res.url || "";
                      const isInternal =
                        res.is_internal ||
                        !url ||
                        url.includes("learn.internal") ||
                        url.startsWith("/") ||
                        url.startsWith("internal:");
                      const hasExternalUrl =
                        !isInternal && /^https?:\/\//i.test(url);

                      if (hasExternalUrl) {
                        return (
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
                          >
                            <span>Study Online</span>
                            <span>↗</span>
                          </a>
                        );
                      }

                      if (res.id || res.concept_id) {
                        return (
                          <Link
                            to={`/resources/${res.id || res.concept_id}`}
                            className="inline-flex items-center space-x-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
                          >
                            <span>Study Notes</span>
                            <span>→</span>
                          </Link>
                        );
                      }

                      return (
                        <button
                          disabled
                          className="inline-flex items-center space-x-1 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 rounded-xl text-xs font-semibold cursor-not-allowed border border-gray-200 dark:border-gray-700"
                        >
                          <span>Material Pending</span>
                        </button>
                      );
                    })()}
                  </div>
                </div>
              );
            })}

            {filteredResources.length === 0 && (
              <div className="col-span-full p-16 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 text-gray-500 space-y-2">
                <div className="text-2xl">🔍</div>
                <h4 className="font-bold text-gray-900 dark:text-white text-sm">No Resources Found</h4>
                <p className="text-xs text-gray-400">
                  {typeFilter === "weak"
                    ? "Great news! You have no diagnosed weak topics requiring urgent remediation."
                    : "No learning materials currently match the selected filter."}
                </p>
                {typeFilter !== "all" && (
                  <button
                    onClick={() => setTypeFilter("all")}
                    className="mt-2 text-xs font-semibold text-purple-600 dark:text-purple-400 hover:underline"
                  >
                    View All Resources
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
