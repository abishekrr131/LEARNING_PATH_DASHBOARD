import React from 'react';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Target,
  BookOpen,
  RotateCcw
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import { useLearning } from '../../context/LearningContext';

export const AssessmentResultPage = ({ navigateTo }) => {
  const { assessmentResult } = useLearning();

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-brand-950 to-indigo-950 text-white p-6 sm:p-8 border border-slate-800 shadow-2xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 z-10 relative">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-brand-500/20 border border-brand-400/30 text-brand-300 text-xs font-semibold mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI Diagnostic Complete</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Assessment Analytics & Skill Profile
            </h1>
            <p className="text-xs text-slate-300 mt-1">
              Here is your personalized full-stack skill breakdown evaluated by our diagnostic engine.
            </p>
          </div>

          <button
            onClick={() => navigateTo('/learning-path')}
            className="py-3 px-6 rounded-2xl text-xs font-bold bg-gradient-to-r from-brand-500 via-indigo-500 to-brand-600 hover:from-brand-400 hover:to-indigo-400 text-white shadow-xl shadow-brand-500/30 flex items-center space-x-2 transition-all flex-shrink-0"
          >
            <span>Continue to Personalized Roadmap</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Top 4 KPI Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Overall Score */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
          <div className="w-14 h-14 rounded-2xl bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800 flex items-center justify-center text-brand-600 dark:text-brand-400 flex-shrink-0">
            <Award className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400">Overall Score</span>
            <div className="text-2xl font-black text-slate-900 dark:text-white">
              {assessmentResult.score}%
            </div>
            <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
              {assessmentResult.correctAnswers} / {assessmentResult.totalQuestions} Correct
            </span>
          </div>
        </div>

        {/* Accuracy */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
          <div className="w-14 h-14 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 flex-shrink-0">
            <Target className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400">Diagnostic Accuracy</span>
            <div className="text-2xl font-black text-slate-900 dark:text-white">
              {assessmentResult.accuracy}%
            </div>
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              High Precision Rating
            </span>
          </div>
        </div>

        {/* Learning Readiness */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 flex-shrink-0">
            <TrendingUp className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400">Learning Readiness</span>
            <div className="text-2xl font-black text-slate-900 dark:text-white">
              {assessmentResult.readinessScore} / 100
            </div>
            <span className="text-[11px] font-semibold text-brand-600 dark:text-brand-400">
              Ready for React & Node
            </span>
          </div>
        </div>

        {/* Recommended Focus */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm flex items-center space-x-4">
          <div className="w-14 h-14 rounded-2xl bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 flex items-center justify-center text-amber-600 dark:text-amber-400 flex-shrink-0">
            <BookOpen className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400">Primary Focus</span>
            <div className="text-sm font-bold text-slate-900 dark:text-white truncate">
              {assessmentResult.weakSkills[0] || 'Node.js Streams'}
            </div>
            <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400">
              Targeted Improvement
            </span>
          </div>
        </div>
      </div>

      {/* Visual Analytics Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Topic Score Breakdown Bar Chart */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Topic Mastery Breakdown
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Percentage score achieved across Full Stack modules
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={assessmentResult.topicBreakdown}>
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
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
                <Bar dataKey="score" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Skill Proficiency Radar Chart */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Radar Skill Radar
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Multi-dimensional competency assessment
              </p>
            </div>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={assessmentResult.topicBreakdown}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="name" stroke="#94a3b8" fontSize={10} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#475569" fontSize={9} />
                <Radar
                  name="Proficiency"
                  dataKey="score"
                  stroke="#8b5cf6"
                  fill="#8b5cf6"
                  fillOpacity={0.4}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Mastered vs Weak Skills Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Mastered Skills */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Mastered Concepts
          </h3>
          <div className="flex flex-wrap gap-2">
            {assessmentResult.masteredSkills.map((skill, i) => (
              <span
                key={i}
                className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
              >
                ✓ {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Weak Skills & Recommended Topics */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center text-amber-600 dark:text-amber-400">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Recommended Growth Areas
          </h3>
          <div className="flex flex-wrap gap-2">
            {assessmentResult.weakSkills.map((skill, i) => (
              <span
                key={i}
                className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
              >
                ⚠ {skill}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Retake / Roadmap Buttons */}
      <div className="flex items-center justify-between pt-4">
        <button
          onClick={() => navigateTo('/onboarding')}
          className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all flex items-center space-x-1.5"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Retake Assessment</span>
        </button>

        <button
          onClick={() => navigateTo('/learning-path')}
          className="px-6 py-3 rounded-2xl text-xs font-bold bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-500 hover:from-brand-500 hover:to-indigo-500 text-white shadow-lg shadow-brand-500/25 flex items-center space-x-2 transition-all"
        >
          <span>Unlock Full Stack Roadmap</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
