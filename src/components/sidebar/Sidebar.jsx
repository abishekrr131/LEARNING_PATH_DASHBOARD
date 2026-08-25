import React from 'react';
import {
  LayoutDashboard,
  Map,
  Award,
  TrendingUp,
  BookOpen,
  User,
  LogOut,
  Sparkles,
  ChevronRight
} from 'lucide-react';
import { useLearning } from '../../context/LearningContext';

export const Sidebar = ({ currentPath, navigateTo }) => {
  const { logout, profile } = useLearning();

  const navItems = [
    { label: 'Dashboard', path: '/home', icon: LayoutDashboard },
    { label: 'Learning Path', path: '/learning-path', icon: Map, badge: 'Active' },
    { label: 'Assessments', path: '/assessments', icon: Award },
    { label: 'Progress & Analytics', path: '/progress', icon: TrendingUp },
    { label: 'Resources', path: '/resources', icon: BookOpen },
    { label: 'Profile & Settings', path: '/profile', icon: User }
  ];

  return (
    <aside className="w-64 border-r border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md flex flex-col justify-between hidden md:flex min-h-[calc(100vh-4rem)] p-4 transition-colors">
      {/* Navigation Links */}
      <div className="space-y-1">
        <p className="px-3 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
          Navigation
        </p>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPath === item.path;

          return (
            <button
              key={item.path}
              onClick={() => navigateTo(item.path)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all group ${
                isActive
                  ? 'bg-brand-500 text-white shadow-md shadow-brand-500/25 font-bold'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon
                  className={`w-4 h-4 transition-transform group-hover:scale-110 ${
                    isActive ? 'text-white' : 'text-slate-400 group-hover:text-brand-500 dark:text-slate-500'
                  }`}
                />
                <span>{item.label}</span>
              </div>
              {item.badge && !isActive && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-brand-50 text-brand-600 dark:bg-brand-950/60 dark:text-brand-400 border border-brand-200 dark:border-brand-800">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom Profile Summary Card & Logout */}
      <div className="space-y-3 pt-4 border-t border-slate-100 dark:border-slate-800">
        <div className="p-3 rounded-2xl bg-gradient-to-br from-slate-100 to-slate-50 dark:from-slate-800/60 dark:to-slate-900/60 border border-slate-200/80 dark:border-slate-800">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center">
              <Sparkles className="w-3 h-3 text-amber-500 mr-1" />
              {profile.levelTitle}
            </span>
            <span className="text-[10px] font-bold text-brand-600 dark:text-brand-400">
              {profile.xpLevel} XP
            </span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-brand-500 to-indigo-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${(profile.xpLevel / profile.nextLevelXp) * 100}%` }}
            ></div>
          </div>
        </div>

        <button
          onClick={() => {
            logout();
            navigateTo('/login');
          }}
          className="w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-all border border-transparent hover:border-rose-200 dark:hover:border-rose-900/40"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
