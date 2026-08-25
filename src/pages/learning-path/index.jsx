import React, { useState } from 'react';
import {
  FileCode,
  Palette,
  Code,
  Atom,
  Server,
  Layers,
  Database,
  CheckCircle2,
  Lock,
  PlayCircle,
  Award,
  Sparkles,
  BookOpen,
  FolderGit2,
  HelpCircle,
  X,
  ArrowRight
} from 'lucide-react';
import { useLearning } from '../../context/LearningContext';

export const LearningPathPage = ({ navigateTo }) => {
  const { roadmap, setRoadmap, showToast } = useLearning();
  const [activeNode, setActiveNode] = useState(null);

  const iconMap = {
    FileCode,
    Palette,
    Code,
    Atom,
    Server,
    Layers,
    Database
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return (
          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 flex items-center">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Completed
          </span>
        );
      case 'in-progress':
        return (
          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-brand-50 text-brand-600 dark:bg-brand-950/60 dark:text-brand-400 border border-brand-200 dark:border-brand-800 flex items-center animate-pulse">
            <PlayCircle className="w-3 h-3 mr-1" />
            Current Focus
          </span>
        );
      case 'unlocked':
        return (
          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
            Unlocked
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700 flex items-center">
            <Lock className="w-3 h-3 mr-1" />
            Locked
          </span>
        );
    }
  };

  const handleStartNodeQuiz = (node) => {
    if (node.status === 'locked') {
      showToast('Complete preceding modules to unlock this topic!', 'info');
      return;
    }
    showToast(`Launching ${node.title} Module Assessment...`, 'info');
    navigateTo('/assessment');
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-brand-900 via-indigo-900 to-slate-900 text-white p-6 sm:p-8 border border-slate-800 shadow-2xl">
        <div className="max-w-2xl z-10 relative">
          <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/30">
            Personalized Learning Path
          </span>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-3">
            Full Stack Web Developer Roadmap
          </h1>

          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Follow our interactive node progression. Completing topics unlocks next-level frameworks and updates your global skill readiness.
          </p>
        </div>
      </div>

      {/* Interactive Vertical Connected Roadmap Container */}
      <div className="relative pl-4 sm:pl-8 space-y-8 py-4">
        {roadmap.map((node, index) => {
          const IconComp = iconMap[node.icon] || Code;
          const isLast = index === roadmap.length - 1;
          const isCompleted = node.status === 'completed';
          const isInProgress = node.status === 'in-progress';
          const isLocked = node.status === 'locked';

          return (
            <div key={node.id} className="relative flex items-start space-x-4 sm:space-x-6 group">
              {/* Vertical Connecting Line */}
              {!isLast && (
                <div
                  className={`absolute left-5 sm:left-7 top-14 bottom-0 w-1 -ml-0.5 rounded-full transition-all duration-500 ${
                    isCompleted
                      ? 'roadmap-line-completed'
                      : isInProgress
                      ? 'roadmap-line-inprogress'
                      : 'roadmap-line-locked'
                  }`}
                  style={{ height: 'calc(100% + 2rem)' }}
                ></div>
              )}

              {/* Connected Node Avatar Bubble */}
              <div
                onClick={() => setActiveNode(node)}
                className={`relative z-10 w-11 h-11 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center text-white cursor-pointer transition-all duration-300 flex-shrink-0 shadow-lg ${
                  isCompleted
                    ? 'bg-gradient-to-tr from-emerald-500 to-teal-600 shadow-emerald-500/25 ring-4 ring-emerald-500/10'
                    : isInProgress
                    ? 'bg-gradient-to-tr from-brand-600 to-indigo-600 shadow-brand-500/30 ring-4 ring-brand-500/20 scale-110'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
                }`}
              >
                <IconComp className="w-5 h-5 sm:w-7 sm:h-7" />
              </div>

              {/* Main Node Card */}
              <div
                className={`flex-1 bg-white dark:bg-slate-900 border rounded-3xl p-5 sm:p-6 transition-all duration-300 shadow-sm ${
                  isInProgress
                    ? 'border-brand-500/60 dark:border-brand-500/60 ring-2 ring-brand-500/10 shadow-xl'
                    : 'border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                  <div>
                    <div className="flex items-center space-x-3">
                      <h3 className="text-base font-bold text-slate-900 dark:text-white">
                        {node.title}
                      </h3>
                      {getStatusBadge(node.status)}
                    </div>
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mt-0.5">
                      {node.subtitle}
                    </p>
                  </div>

                  {/* Progress Ring / Bar */}
                  <div className="flex items-center space-x-3">
                    <span className="text-xs font-bold text-brand-600 dark:text-brand-400">
                      {node.progress}%
                    </span>
                    <div className="w-24 bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isCompleted
                            ? 'bg-emerald-500'
                            : 'bg-gradient-to-r from-brand-500 to-indigo-600'
                        }`}
                        style={{ width: `${node.progress}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  {node.description}
                </p>

                {/* Sub-metrics Pills */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100 dark:border-slate-800/80">
                  <div className="flex items-center space-x-4 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                    <span className="flex items-center">
                      <BookOpen className="w-3.5 h-3.5 mr-1 text-slate-400" />
                      {node.lessonsCount} Lessons
                    </span>
                    <span className="flex items-center">
                      <FolderGit2 className="w-3.5 h-3.5 mr-1 text-slate-400" />
                      {node.projectsCount} Projects
                    </span>
                    <span className="flex items-center text-brand-600 dark:text-brand-400 font-semibold">
                      <Award className="w-3.5 h-3.5 mr-1" />
                      Quiz: {node.quizScore}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setActiveNode(node)}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all"
                    >
                      View Modules
                    </button>

                    {!isLocked && (
                      <button
                        onClick={() => handleStartNodeQuiz(node)}
                        className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20 flex items-center space-x-1 transition-all"
                      >
                        <span>Take Quiz</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Node Details Drawer Modal */}
      {activeNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setActiveNode(null)}
              className="absolute top-4 right-4 p-1.5 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-brand-500 text-white flex items-center justify-center">
                <Code className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {activeNode.title}
                </h3>
                <p className="text-xs text-slate-500">{activeNode.subtitle}</p>
              </div>
            </div>

            <div className="space-y-3 my-4 max-h-60 overflow-y-auto pr-1">
              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                Core Module Syllabus
              </h4>
              <div className="space-y-2">
                {activeNode.skills.map((skill, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 flex items-center justify-between text-xs font-medium text-slate-700 dark:text-slate-300"
                  >
                    <span className="flex items-center">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mr-2" />
                      {skill}
                    </span>
                    <span className="text-[10px] text-slate-400">Lesson #{idx + 1}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex space-x-3 pt-2">
              <button
                onClick={() => setActiveNode(null)}
                className="flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700"
              >
                Close
              </button>
              <button
                onClick={() => {
                  setActiveNode(null);
                  handleStartNodeQuiz(activeNode);
                }}
                className="flex-1 py-2.5 px-4 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20"
              >
                Start Topic Assessment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
