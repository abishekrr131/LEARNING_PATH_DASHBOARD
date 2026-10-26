import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export default function MainLayout({ children, currentConcept = null }) {
  const { user, profile, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Stacked in exact user-flow order per Master Prompt Requirement 6
  const navItems = [
    { name: "Dashboard", path: "/dashboard", icon: "📊" },
    { name: "Assessments Hub", path: "/assessments", icon: "🎯" },
    { name: "Learning Path", path: "/learning-path", icon: "🗺️" },
    { name: "Weak Topics", path: "/weak-topics", icon: "📉" },
    { name: "Root Cause", path: "/root-cause", icon: "🧬" },
    { name: "Schedule", path: "/schedule", icon: "📅" },
    { name: "Resources", path: "/resources", icon: "📚" },
    { name: "Practice Mode", path: "/practice", icon: "✍️" },
    { name: "Progress & Readiness", path: "/progress", icon: "📈" },
    { name: "Settings", path: "/settings", icon: "⚙️" },
  ];

  const currentPage = navItems.find((n) => n.path === location.pathname)?.name || "Dashboard";

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col md:flex-row transition-colors duration-200">
      {/* Mobile Top Header */}
      <div className="md:hidden sticky top-0 z-40 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-b border-purple-100 dark:border-purple-900/40 px-4 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <button
            type="button"
            onClick={() => setMobileDrawerOpen(true)}
            className="p-2 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            ☰
          </button>
          <Link to="/dashboard" className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-rose-500 flex items-center justify-center text-white font-black text-sm shadow-md shadow-purple-500/20">
              P
            </div>
            <span className="font-extrabold text-sm tracking-tight bg-gradient-to-r from-purple-700 via-indigo-600 to-rose-600 bg-clip-text text-transparent dark:from-purple-400 dark:to-rose-400">
              RCT-GAT
            </span>
          </Link>
        </div>

        <div className="flex items-center space-x-2">
          {profile?.target_name && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 truncate max-w-[120px]">
              {profile.target_name}
            </span>
          )}
          <button
            type="button"
            onClick={toggleTheme}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 dark:text-gray-400"
          >
            {isDark ? "☀️" : "🌙"}
          </button>
        </div>
      </div>

      {/* Desktop Vertical Left Sidebar (Fixed-width, top-to-bottom) */}
      <aside className="hidden md:flex w-64 shrink-0 h-screen sticky top-0 flex-col justify-between border-r border-purple-100 dark:border-purple-900/30 bg-white dark:bg-gray-900 z-30 p-4">
        {/* Top: Logo, Exam Badge, Theme Toggle */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2 pt-2">
            <Link to="/dashboard" className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-rose-500 flex items-center justify-center text-white font-black text-lg shadow-md shadow-purple-500/20">
                P
              </div>
              <div>
                <span className="font-black text-base tracking-tight bg-gradient-to-r from-purple-700 via-indigo-600 to-rose-600 bg-clip-text text-transparent dark:from-purple-400 dark:to-rose-400 block leading-tight">
                  RCT-GAT
                </span>
                <span className="text-[10px] text-gray-400 font-mono">Adaptive Roadmap</span>
              </div>
            </Link>

            <button
              type="button"
              onClick={toggleTheme}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title="Toggle theme"
            >
              {isDark ? "☀️" : "🌙"}
            </button>
          </div>

          {/* Exam Target Badge */}
          <div className="px-2">
            <div className="p-2.5 rounded-xl bg-purple-50/80 dark:bg-purple-950/40 border border-purple-100 dark:border-purple-900/60">
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 block">
                Target Exam Track
              </span>
              <span className="text-xs font-bold text-gray-800 dark:text-gray-200 truncate block mt-0.5">
                {profile?.target_name || "Banking (IBPS PO)"}
              </span>
            </div>
          </div>

          {/* Navigation Items Stacked in User-Flow Order */}
          <nav className="space-y-1 px-1 pt-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-500/20 font-bold"
                      : "text-gray-600 dark:text-gray-400 hover:text-purple-700 dark:hover:text-purple-300 hover:bg-purple-50/60 dark:hover:bg-gray-800/60"
                  }`}
                >
                  <span className="text-base">{item.icon}</span>
                  <span className="truncate">{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Pinned User Profile & Sign Out */}
        <div className="pt-4 border-t border-gray-100 dark:border-gray-800 px-2 space-y-2">
          <div className="flex items-center space-x-2.5 px-1 py-1">
            <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 font-bold flex items-center justify-center text-xs shrink-0">
              {user?.name ? user.name[0].toUpperCase() : "U"}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-bold text-gray-900 dark:text-white truncate">
                {user?.name || "Learner"}
              </div>
              <div className="text-[10px] text-gray-400 truncate">
                {user?.email || "learner@example.com"}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={logout}
            className="w-full py-2 px-3 rounded-xl border border-gray-200 dark:border-gray-800 hover:border-rose-300 dark:hover:border-rose-900 hover:bg-rose-50/50 dark:hover:bg-rose-950/20 text-gray-600 dark:text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 text-xs font-semibold transition-colors flex items-center justify-center space-x-1.5"
          >
            <span>🚪</span>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileDrawerOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setMobileDrawerOpen(false)}
          />
          <div className="relative w-72 max-w-[80vw] bg-white dark:bg-gray-900 h-full shadow-2xl flex flex-col justify-between p-5 border-r border-purple-100 dark:border-purple-900/40 z-10 animate-slide-in">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800">
                <Link
                  to="/dashboard"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="flex items-center space-x-2"
                >
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center text-white font-bold text-sm">
                    P
                  </div>
                  <span className="font-extrabold text-sm text-gray-900 dark:text-white">RCT-GAT</span>
                </Link>
                <button
                  type="button"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="p-1 rounded-lg text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {profile?.target_name && (
                <div className="p-2.5 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-xs font-bold text-purple-700 dark:text-purple-300">
                  {profile.target_name}
                </div>
              )}

              <nav className="space-y-1">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileDrawerOpen(false)}
                      className={`flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold ${
                        isActive
                          ? "bg-purple-600 text-white font-bold"
                          : "text-gray-700 dark:text-gray-300 hover:bg-purple-50 dark:hover:bg-gray-800"
                      }`}
                    >
                      <span>{item.icon}</span>
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            <div className="pt-4 border-t border-gray-100 dark:border-gray-800 space-y-2">
              <div className="text-xs font-bold text-gray-800 dark:text-gray-200">
                {user?.name || "Learner"}
              </div>
              <button
                type="button"
                onClick={logout}
                className="w-full py-2 px-3 rounded-xl border border-gray-200 dark:border-gray-700 text-xs text-rose-600 font-semibold"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 min-w-0 flex flex-col min-h-screen">
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
