import React, { useState } from 'react';
import {
  TrendingUp,
  Clock,
  Flame,
  Award,
  BookOpen,
  Building2,
  Sparkles,
  CheckCircle2,
  Calendar,
  DollarSign,
  Activity,
  Briefcase
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  AreaChart,
  Area,
  BarChart,
  Bar
} from 'recharts';
import { INDUSTRY_METRICS } from '../../data/dummyData';
import { useLearning } from '../../context/LearningContext';

export const ProgressPage = () => {
  const { profile } = useLearning();
  const [activeTab, setActiveTab] = useState('all'); // all, weekly, monthly, industry

  const weeklyTrendData = [
    { day: 'Mon', hours: 2.5, completed: 3 },
    { day: 'Tue', hours: 4.0, completed: 5 },
    { day: 'Wed', hours: 3.2, completed: 4 },
    { day: 'Thu', hours: 5.5, completed: 7 },
    { day: 'Fri', hours: 4.8, completed: 6 },
    { day: 'Sat', hours: 6.2, completed: 8 },
    { day: 'Sun', hours: 3.0, completed: 4 }
  ];

  const monthlyTrendData = [
    { week: 'Week 1', hours: 14.5, mastery: 45 },
    { week: 'Week 2', hours: 18.2, mastery: 62 },
    { week: 'Week 3', hours: 22.0, mastery: 74 },
    { week: 'Week 4', hours: 28.5, mastery: 85 }
  ];

  const recentActivities = [
    { id: 1, action: 'Completed Quiz: JavaScript Async & Promises', score: '90%', time: '2 hours ago', icon: Award },
    { id: 2, action: 'Finished Lesson: CSS Flexbox Layouts', score: '100%', time: 'Yesterday', icon: CheckCircle2 },
    { id: 3, action: 'Reached 14-Day Consecutive Streak 🔥', score: '+100 XP', time: '2 days ago', icon: Flame },
    { id: 4, action: 'Unlocked Certificate: Full Stack Foundations', score: 'Verified', time: '3 days ago', icon: Sparkles }
  ];

  const achievementsList = [
    { title: 'HTML Hero', desc: '100% Score on HTML5 Test', unlocked: true, icon: '🏆' },
    { title: 'Streak Master', desc: '14 Consecutive Learning Days', unlocked: true, icon: '🔥' },
    { title: 'React Pioneer', desc: 'Complete React Components', unlocked: false, icon: '⚛️' },
    { title: 'Node Architect', desc: 'Master Event Loop & Streams', unlocked: false, icon: '🟢' }
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950 to-brand-950 text-white p-6 sm:p-8 border border-slate-800 shadow-2xl">
        <div className="max-w-2xl z-10 relative">
          <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/30">
            Analytics & Insights
          </span>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-3">
            Learning Progress & Industry Dashboard
          </h1>

          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Track your personal study metrics, weekly study trends, unlocked badges, and real-world tech industry demand statistics.
          </p>
        </div>
      </div>

      {/* 1. OVERVIEW SECTION: Key Metrics Grid */}
      <div>
        <h2 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4 flex items-center">
          <Activity className="w-4 h-4 mr-2 text-brand-500" />
          1. Overview Metrics
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800 flex items-center justify-center text-brand-600 dark:text-brand-400 flex-shrink-0">
              <Clock className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Total Learning Hours</span>
              <div className="text-xl font-black text-slate-900 dark:text-white">42.5 hrs</div>
              <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">+5.2 hrs this week</span>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 flex items-center justify-center text-amber-600 dark:text-amber-400 flex-shrink-0">
              <Flame className="w-6 h-6 fill-amber-500 text-amber-500" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Current Streak</span>
              <div className="text-xl font-black text-slate-900 dark:text-white">{profile.streakDays} Days 🔥</div>
              <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400">Top 5% Active Learners</span>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 flex-shrink-0">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Courses Completed</span>
              <div className="text-xl font-black text-slate-900 dark:text-white">8 Courses</div>
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">52% Total Roadmap</span>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 flex-shrink-0">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Earned Experience</span>
              <div className="text-xl font-black text-slate-900 dark:text-white">{profile.xpLevel} XP</div>
              <span className="text-[11px] font-semibold text-brand-600 dark:text-brand-400">Level 8 Specialist</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. WEEKLY & MONTHLY PROGRESS CHARTS SECTION */}
      <div>
        <h2 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4 flex items-center">
          <Calendar className="w-4 h-4 mr-2 text-brand-500" />
          2. Weekly & Monthly Study Trends
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Weekly Progress Line Chart */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Daily Study Hours (This Week)</h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Time spent practicing interactive modules</p>
              </div>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weeklyTrendData}>
                  <XAxis dataKey="day" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '12px'
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="hours"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    dot={{ fill: '#3b82f6', r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Monthly Mastery Area Chart */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Monthly Skill Growth Rate</h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Cumulative percentage skill mastery</p>
              </div>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthlyTrendData}>
                  <XAxis dataKey="week" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '12px'
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="mastery"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.2}
                    strokeWidth={3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* 3. INDUSTRY DASHBOARD SECTION */}
      <div>
        <h2 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4 flex items-center">
          <Briefcase className="w-4 h-4 mr-2 text-indigo-500" />
          3. Tech Industry Dashboard & Market Insights
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tech Popularity Bar Chart */}
          <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Framework Popularity Index 2026</h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Based on global tech job postings & Github activity</p>
              </div>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={INDUSTRY_METRICS.popularityChart}>
                  <XAxis dataKey="skill" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '12px'
                    }}
                  />
                  <Bar dataKey="score" fill="#6366f1" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Salary Trends */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-emerald-600 dark:text-emerald-400 mb-2">
                <DollarSign className="w-5 h-5" />
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Full Stack Salary Trends</h3>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-4">Average market compensation tiers</p>

              <div className="space-y-3">
                {INDUSTRY_METRICS.salaryTrends.map((tier, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/60 flex items-center justify-between"
                  >
                    <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{tier.level}</span>
                    <span className="text-xs font-extrabold text-emerald-600 dark:text-emerald-400">{tier.salary}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Top Hiring Companies */}
        <div className="mt-6 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold text-slate-900 dark:text-white flex items-center">
              <Building2 className="w-4 h-4 mr-2 text-brand-500" />
              Top Companies Hiring Full Stack Engineers
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {INDUSTRY_METRICS.topCompanies.map((comp, i) => (
              <div
                key={i}
                className="p-4 rounded-2xl bg-slate-50/70 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/60 space-y-2 text-center"
              >
                <div className="w-10 h-10 rounded-xl bg-slate-900 text-white dark:bg-slate-700 font-extrabold text-sm flex items-center justify-center mx-auto shadow-sm">
                  {comp.logo}
                </div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white">{comp.name}</h4>
                <p className="text-[10px] font-bold text-brand-600 dark:text-brand-400">{comp.openRoles}</p>
                <p className="text-[10px] text-slate-400 line-clamp-1">{comp.techStack}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. RECENT ACTIVITY & 5. ACHIEVEMENTS SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity Feed */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
          <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
            4. Recent Activity Log
          </h3>

          <div className="space-y-3">
            {recentActivities.map((act) => {
              const IconComp = act.icon;
              return (
                <div
                  key={act.id}
                  className="p-3.5 rounded-2xl bg-slate-50/60 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/60 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-xl bg-brand-500/10 text-brand-500 flex items-center justify-center flex-shrink-0">
                      <IconComp className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800 dark:text-slate-200">{act.action}</p>
                      <span className="text-[10px] text-slate-400">{act.time}</span>
                    </div>
                  </div>

                  <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                    {act.score}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Achievements Badges */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
          <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
            5. Unlocked Achievements
          </h3>

          <div className="grid grid-cols-2 gap-3">
            {achievementsList.map((badge, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-2xl border flex items-center space-x-3 ${
                  badge.unlocked
                    ? 'bg-amber-50/40 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60'
                    : 'bg-slate-50 dark:bg-slate-800/30 border-slate-200 dark:border-slate-800 opacity-60'
                }`}
              >
                <div className="text-2xl">{badge.icon}</div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white">{badge.title}</h4>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400">{badge.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
