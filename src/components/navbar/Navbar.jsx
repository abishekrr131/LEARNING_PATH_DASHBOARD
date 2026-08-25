import React, { useState } from 'react';
import { Sparkles, Search, Bell, Flame, User, Check, X } from 'lucide-react';
import { ThemeToggle } from '../common/ThemeToggle';
import { useLearning } from '../../context/LearningContext';

export const Navbar = ({ navigateTo }) => {
  const { searchQuery, setSearchQuery, profile } = useLearning();
  const [showNotifications, setShowNotifications] = useState(false);

  const notifications = [
    { id: 1, title: 'New Assessment Completed!', time: '10 mins ago', read: false },
    { id: 2, title: 'HTML5 Mastery Badge Unlocked', time: '2 hours ago', read: false },
    { id: 3, title: '14-Day Streak Bonus +100 XP', time: 'Yesterday', read: true }
  ];

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-slate-200/80 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between transition-colors">
      {/* Brand Logo */}
      <div className="flex items-center space-x-3 cursor-pointer" onClick={() => navigateTo('/home')}>
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20">
          <Sparkles className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-slate-900 via-brand-700 to-indigo-600 dark:from-white dark:via-brand-300 dark:to-indigo-400 bg-clip-text text-transparent">
            Pathfinder <span className="text-brand-500 font-black text-xs uppercase px-1.5 py-0.5 rounded bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800">AI</span>
          </span>
        </div>
      </div>

      {/* Global Search Bar */}
      <div className="hidden md:flex items-center flex-1 max-w-md mx-8">
        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
          <input
            type="text"
            placeholder="Quick search domain or skill (e.g. Full Stack)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-12 py-2 text-sm bg-slate-100/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 transition-all text-slate-800 dark:text-slate-200 placeholder-slate-400"
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-slate-400 bg-slate-200/60 dark:bg-slate-700 px-1.5 py-0.5 rounded border border-slate-300 dark:border-slate-600">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-3">
        {/* Streak Counter */}
        <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 rounded-xl text-amber-600 dark:text-amber-400 text-xs font-semibold">
          <Flame className="w-4 h-4 fill-amber-500 text-amber-500" />
          <span>{profile.streakDays} Day Streak</span>
        </div>

        <ThemeToggle />

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all border border-slate-200/80 dark:border-slate-800 relative"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4 text-slate-600 dark:text-slate-300" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-white dark:ring-slate-900 animate-ping"></span>
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500"></span>
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 p-4 z-50 animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <h4 className="font-semibold text-sm text-slate-800 dark:text-slate-100">Notifications</h4>
                <button
                  onClick={() => setShowNotifications(false)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="divide-y divide-slate-100 dark:divide-slate-800 my-2 max-h-60 overflow-y-auto">
                {notifications.map((item) => (
                  <div key={item.id} className="py-2.5 flex items-start space-x-3 text-xs">
                    <div className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 flex-shrink-0"></div>
                    <div className="flex-1">
                      <p className="font-medium text-slate-700 dark:text-slate-200">{item.title}</p>
                      <span className="text-[10px] text-slate-400">{item.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Profile Pill */}
        <div
          onClick={() => navigateTo('/profile')}
          className="flex items-center space-x-2.5 p-1 pl-2.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 cursor-pointer transition-all"
        >
          <div className="text-right hidden sm:block">
            <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">{profile.name}</p>
            <p className="text-[10px] text-slate-400 font-medium">{profile.xpLevel} XP</p>
          </div>
          <img
            src={profile.avatar}
            alt={profile.name}
            className="w-8 h-8 rounded-full object-cover ring-2 ring-brand-500/40"
          />
        </div>
      </div>
    </header>
  );
};
