import React, { useState } from 'react';
import {
  Award,
  Trophy,
  Flame,
  CheckCircle2,
  XCircle,
  Play,
  Filter,
  Calendar,
  Clock,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { LEADERBOARD_DATA, TOPICS } from '../../data/dummyData';
import { useLearning } from '../../context/LearningContext';

export const AssessmentsPage = ({ navigateTo }) => {
  const { assessmentHistory, setOnboardingData, showToast } = useLearning();
  const [activeTab, setActiveTab] = useState('start'); // 'start' or 'history'
  const [historyFilter, setHistoryFilter] = useState('All'); // All, Passed, Failed, Initial Assessment, Weekly Assessments

  // Filter history logs
  const filteredHistory = assessmentHistory.filter((item) => {
    if (historyFilter === 'All') return true;
    if (historyFilter === 'Passed') return item.status === 'Passed';
    if (historyFilter === 'Failed') return item.status === 'Failed';
    if (historyFilter === 'Initial Assessment') return item.type === 'Initial Assessment';
    if (historyFilter === 'Weekly Assessments') return item.type === 'Weekly Assessments';
    return true;
  });

  const handleStartTopicAssessment = (topicName) => {
    setOnboardingData((prev) => ({
      ...prev,
      questionsCount: 20
    }));
    showToast(`Launching ${topicName} Assessment...`, 'info');
    navigateTo('/assessment');
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950 to-brand-950 text-white p-6 sm:p-8 border border-slate-800 shadow-2xl">
        <div className="max-w-2xl z-10 relative">
          <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-400/30 flex items-center w-max mb-3">
            <Trophy className="w-3.5 h-3.5 mr-1" />
            Competitive Leaderboard & Quizzes
          </span>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Assessments & Global Leaderboard
          </h1>

          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Test your full stack expertise with timed diagnostic quizzes, earn XP, unlock verified certificates, and rise through the global ranks.
          </p>
        </div>
      </div>

      {/* TOP SECTION: LEADERBOARD */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center uppercase tracking-wider">
            <Trophy className="w-4 h-4 mr-2 text-amber-500" />
            Global Student Leaderboard (This Week)
          </h2>
          <span className="text-xs font-semibold text-brand-600 dark:text-brand-400">
            Updated Hourly
          </span>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-800/80 overflow-x-auto">
          {LEADERBOARD_DATA.map((user) => {
            const isTop3 = user.rank <= 3;
            const trophyIcons = ['🥇', '🥈', '🥉'];

            return (
              <div
                key={user.rank}
                className={`py-3 px-4 flex items-center justify-between text-xs rounded-2xl transition-colors ${
                  user.isUser
                    ? 'bg-brand-50/80 dark:bg-brand-950/50 border border-brand-500/40 font-bold'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center space-x-4">
                  <span className="w-6 font-extrabold text-slate-500 text-center">
                    {isTop3 ? trophyIcons[user.rank - 1] : `#${user.rank}`}
                  </span>

                  <img
                    src={user.avatar}
                    alt={user.name}
                    className="w-8 h-8 rounded-full object-cover ring-2 ring-slate-200 dark:ring-slate-700"
                  />

                  <div>
                    <h4 className="font-bold text-slate-900 dark:text-white flex items-center">
                      {user.name}
                      {user.isUser && (
                        <span className="ml-2 text-[10px] px-1.5 py-0.2 rounded bg-brand-500 text-white font-extrabold">
                          You
                        </span>
                      )}
                    </h4>
                    <span className="text-[10px] text-slate-400">{user.badge}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-6">
                  <div className="text-right hidden sm:block">
                    <p className="font-bold text-slate-700 dark:text-slate-200">{user.coursesCompleted} Courses</p>
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400">{user.weeklyRank} Rank</span>
                  </div>

                  <div className="text-right">
                    <span className="font-black text-brand-600 dark:text-brand-400 text-sm">
                      {user.xp} XP
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* BELOW LEADERBOARD: TWO TABS */}
      <div className="space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-200 dark:border-slate-800 pb-2">
          <button
            onClick={() => setActiveTab('start')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'start'
                ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Start Assessment
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'history'
                ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Assessment History ({assessmentHistory.length})
          </button>
        </div>

        {/* TAB 1: START ASSESSMENT */}
        {activeTab === 'start' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 animate-in fade-in duration-200">
            {TOPICS.map((topic) => (
              <div
                key={topic.id}
                className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm hover:shadow-xl transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-extrabold uppercase tracking-wider text-brand-600 dark:text-brand-400 px-2.5 py-0.5 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800">
                      {topic.name}
                    </span>
                    <span className="text-[10px] font-semibold text-slate-400">20 Qs • 15 Mins</span>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                    {topic.name} Mastery Assessment
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                    {topic.description}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                    +250 XP Award
                  </span>

                  <button
                    onClick={() => handleStartTopicAssessment(topic.name)}
                    className="py-2 px-3.5 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20 flex items-center space-x-1 transition-all"
                  >
                    <span>Start Test</span>
                    <Play className="w-3 h-3 fill-current" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* TAB 2: ASSESSMENT HISTORY (WITH REFINED FILTERS) */}
        {activeTab === 'history' && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4 animate-in fade-in duration-200">
            {/* Filter Chips */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 flex items-center mr-2">
                <Filter className="w-3.5 h-3.5 mr-1" />
                Filter Logs:
              </span>
              {['All', 'Passed', 'Failed', 'Initial Assessment', 'Weekly Assessments'].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setHistoryFilter(filter)}
                  className={`text-xs font-semibold px-3 py-1 rounded-xl transition-all ${
                    historyFilter === filter
                      ? 'bg-brand-500 text-white shadow-sm'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>

            {/* Assessment History Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold text-[11px] uppercase">
                    <th className="py-3 px-3">Assessment Name</th>
                    <th className="py-3 px-3">Topic</th>
                    <th className="py-3 px-3">Date</th>
                    <th className="py-3 px-3">Marks</th>
                    <th className="py-3 px-3">Percentage</th>
                    <th className="py-3 px-3">Time</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {filteredHistory.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="py-3.5 px-3 font-bold text-slate-900 dark:text-white">
                        {row.name}
                      </td>
                      <td className="py-3.5 px-3 text-slate-600 dark:text-slate-400">
                        <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-semibold text-[10px]">
                          {row.topic}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 text-slate-500">{row.date}</td>
                      <td className="py-3.5 px-3 font-semibold text-slate-800 dark:text-slate-200">
                        {row.marks}
                      </td>
                      <td className="py-3.5 px-3 font-bold text-brand-600 dark:text-brand-400">
                        {row.percentage}%
                      </td>
                      <td className="py-3.5 px-3 text-slate-500">{row.timeTaken}</td>
                      <td className="py-3.5 px-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            row.status === 'Passed'
                              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                              : 'bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800'
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 text-right">
                        <button
                          onClick={() => navigateTo('/assessment-result')}
                          className="text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline"
                        >
                          View Analytics
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
