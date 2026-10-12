import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Landing() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Header */}
      <header className="max-w-7xl mx-auto w-full px-6 py-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-rose-500 flex items-center justify-center text-white font-black text-xl shadow-md shadow-purple-500/20">
            P
          </div>
          <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-purple-700 via-indigo-600 to-rose-600 bg-clip-text text-transparent dark:from-purple-400 dark:to-rose-400">
            RCT-GAT
          </span>
        </div>

        <Link
          to={isAuthenticated ? "/dashboard" : "/login"}
          className="px-5 py-2.5 rounded-xl font-semibold text-sm bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20 transition-all"
        >
          {isAuthenticated ? "Go to Dashboard →" : "Sign In with Google"}
        </Link>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-16 text-center flex flex-col items-center justify-center">
        <div className="inline-flex items-center px-4 py-1.5 rounded-full text-xs font-semibold tracking-wide bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 mb-8">
          ✦ Root-Cause Temporal Graph Attention Network (RCT-GAT)
        </div>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight leading-tight max-w-4xl">
          Adaptive learning that treats the{" "}
          <span className="bg-gradient-to-r from-purple-600 via-indigo-600 to-rose-500 bg-clip-text text-transparent">
            root cause
          </span>
          , not just the symptom.
        </h1>

        <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mt-6 leading-relaxed">
          Traditional platforms repeat questions you got wrong. RCT-GAT uses graph attention over prerequisite dependency DAGs to isolate the foundational misconception causing your error.
        </p>

        {/* Dual Track Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl mt-12 text-left">
          <div className="p-6 rounded-2xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl shadow-purple-500/5">
            <div className="text-3xl mb-3">💻</div>
            <h3 className="font-bold text-lg text-gray-900 dark:text-white">IT & Software Careers</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-4">
              Production-grade competency DAGs for specialized software engineering roles.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {["Machine Learning", "Full Stack Development", "Cyber Security", "GenAI"].map((t) => (
                <span key={t} className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-900/40 shadow-xl shadow-purple-500/5">
            <div className="text-3xl mb-3">🏛️</div>
            <h3 className="font-bold text-lg text-gray-900 dark:text-white">Government Competitive Exams</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-4">
              Structured syllabi with rigorous prerequisites for high-stakes examinations.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {["UPSC Civil Services", "SSC CGL", "Banking (IBPS/SBI)"].map((t) => (
                <span key={t} className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-12">
          <Link
            to={isAuthenticated ? "/dashboard" : "/login"}
            className="inline-flex items-center space-x-2 px-8 py-4 rounded-xl font-bold text-base bg-gradient-to-r from-purple-600 via-indigo-600 to-rose-500 hover:from-purple-700 hover:to-rose-600 text-white shadow-xl shadow-purple-500/25 transition-all transform hover:-translate-y-0.5"
          >
            <span>Your Learning Journey Starts Here</span>
            <span>→</span>
          </Link>
          <p className="text-xs text-gray-400 mt-3">
            Informed Research Trial · Millisecond Behavioural Tracking · Zero Future Leakage
          </p>
        </div>
      </main>
    </div>
  );
}
