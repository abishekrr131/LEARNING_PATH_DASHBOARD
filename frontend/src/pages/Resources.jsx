import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import { learningApi } from "../api/client";

export default function Resources() {
  const [searchParams] = useSearchParams();
  const conceptIdParam = searchParams.get("concept_id");

  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [typeFilter, setTypeFilter] = useState("all");

  useEffect(() => {
    setLoading(true);
    learningApi
      .getResources(conceptIdParam ? parseInt(conceptIdParam) : null)
      .then((data) => {
        setResources(data.resources || []);
      })
      .catch((err) => setError(err.message || "Failed to load resources"))
      .finally(() => setLoading(false));
  }, [conceptIdParam]);

  const filteredResources = resources.filter((r) => {
    if (typeFilter === "all") return true;
    return r.resource_type.toLowerCase() === typeFilter.toLowerCase();
  });

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
            Curated Remediation Resources
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Precision learning materials mapped to your diagnosed knowledge gaps and root-cause prerequisites.
          </p>
          {conceptIdParam && (
            <div className="mt-2 inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">
              Filtered for Concept #{conceptIdParam}
            </div>
          )}
        </div>

        {/* Type Filter Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {["all", "article", "video", "doc", "course"].map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition-colors ${
                typeFilter === t
                  ? "bg-purple-600 text-white shadow-sm"
                  : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {loading && (
          <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Retrieving curated materials…</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredResources.map((res) => (
              <div
                key={res.id}
                className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm flex flex-col justify-between hover:border-purple-200 dark:hover:border-purple-800 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-100 dark:border-purple-900">
                      {res.resource_type}
                    </span>
                    <span className="text-[11px] text-gray-400 capitalize">
                      {res.difficulty_level || "intermediate"}
                    </span>
                  </div>

                  <h3 className="font-bold text-gray-900 dark:text-white text-base line-clamp-2">
                    {res.title}
                  </h3>
                  <p className="text-xs text-purple-600 dark:text-purple-400 font-medium mt-1">
                    {res.concept_name}
                  </p>

                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 line-clamp-3">
                    {res.description}
                  </p>

                  <div className="mt-4 p-2.5 rounded-xl bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/40">
                    <span className="text-[10px] font-bold text-purple-700 dark:text-purple-300 uppercase tracking-wider block">
                      Why Recommended
                    </span>
                    <p className="text-xs text-purple-900 dark:text-purple-200 mt-0.5">
                      {res.why_recommended}
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
                  <span className="text-[11px] text-gray-400">
                    Source: {res.source || "Curated"}
                  </span>
                  <a
                    href={res.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                  >
                    <span>Study Now</span>
                    <span>↗</span>
                  </a>
                </div>
              </div>
            ))}

            {filteredResources.length === 0 && (
              <div className="col-span-full p-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 text-gray-500">
                No resources found matching criteria.
              </div>
            )}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
