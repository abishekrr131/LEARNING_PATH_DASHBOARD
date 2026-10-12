import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import FloatingGemini from "../components/FloatingGemini";

export default function MainLayout({ children, currentConcept = null }) {
  const { user, profile, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { name: "Dashboard", path: "/dashboard", icon: "📊" },
    { name: "Learning Path", path: "/learning-path", icon: "🗺️" },
    { name: "Weak Topics", path: "/weak-topics", icon: "📉" },
    { name: "Root Cause", path: "/root-cause", icon: "🧬" },
    { name: "Assessments Hub", path: "/assessments", icon: "🎯" },
    { name: "Schedule", path: "/schedule", icon: "📅" },
    { name: "Resources", path: "/resources", icon: "📚" },
    { name: "Practice", path: "/practice", icon: "✍️" },
    { name: "Progress", path: "/progress", icon: "📈" },
    { name: "Settings", path: "/settings", icon: "⚙️" },
  ];

  const currentPage = navItems.find((n) => n.path === location.pathname)?.name || "Dashboard";

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col transition-colors duration-200">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-30 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-b border-purple-100 dark:border-purple-900/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <Link to="/dashboard" className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-rose-500 flex items-center justify-center text-white font-black text-lg shadow-md shadow-purple-500/20">
                P
              </div>
              <span className="font-extrabold text-base tracking-tight bg-gradient-to-r from-purple-700 via-indigo-600 to-rose-600 bg-clip-text text-transparent dark:from-purple-400 dark:to-rose-400">
                RCT-GAT
              </span>
            </Link>

            {/* Target Badge */}
            {profile?.target_name && (
              <span className="hidden md:inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                {profile.target_name}
              </span>
            )}
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden lg:flex items-center space-x-1">
            {navItems.slice(0, 7).map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-purple-100 dark:bg-purple-900/50 text-purple-900 dark:text-purple-200 font-bold"
                      : "text-gray-600 dark:text-gray-400 hover:text-purple-700 dark:hover:text-purple-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
                >
                  <span className="mr-1">{item.icon}</span>
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User Controls */}
          <div className="flex items-center space-x-3">
            {/* Dark Mode Toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              className="w-9 h-9 rounded-lg flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title="Toggle theme"
            >
              {isDark ? "☀️" : "🌙"}
            </button>

            {/* Profile Dropdown / Actions */}
            <div className="flex items-center space-x-2">
              <Link
                to="/settings"
                className="text-xs font-medium text-gray-700 dark:text-gray-300 hidden sm:block max-w-[120px] truncate"
              >
                {user?.name || "Learner"}
              </Link>
              <button
                type="button"
                onClick={logout}
                className="text-xs px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:text-rose-600 hover:border-rose-300 transition-colors"
              >
                Sign out
              </button>
            </div>

            {/* Mobile Menu Toggle */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((p) => !p)}
              className="lg:hidden p-2 rounded-lg text-gray-600 dark:text-gray-300"
            >
              ☰
            </button>
          </div>
        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-gray-100 dark:border-gray-800 p-4 space-y-1 bg-white dark:bg-gray-900">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-purple-50 dark:hover:bg-purple-900/30"
              >
                <span className="mr-2">{item.icon}</span>
                {item.name}
              </Link>
            ))}
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Floating Gemini Assistant (Available on all pages, auto-suppressed during scored tests) */}
      <FloatingGemini
        currentConceptId={currentConcept?.id}
        currentConceptName={currentConcept?.name}
        pageContext={currentPage}
      />
    </div>
  );
}
