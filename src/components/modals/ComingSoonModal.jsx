import React from 'react';
import { X, Sparkles, Clock, BellRing, ArrowRight } from 'lucide-react';
import { useLearning } from '../../context/LearningContext';

export const ComingSoonModal = ({ domain, onClose }) => {
  const { showToast } = useLearning();

  if (!domain) return null;

  const handleNotifyMe = () => {
    showToast(`You will be notified when ${domain.title} launches!`, 'success');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl relative text-center">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white mx-auto mb-4 shadow-lg shadow-indigo-500/30">
          <Clock className="w-8 h-8 animate-spin-slow" />
        </div>

        <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
          Under Construction
        </span>

        <h3 className="text-xl font-bold text-slate-900 dark:text-white mt-3 mb-2">
          {domain.title}
        </h3>

        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-6">
          Our AI curriculum engineers are crafting custom interactive assessments, projects, and adaptive roadmaps for <strong className="text-slate-800 dark:text-slate-200">{domain.title}</strong>. Launching Q4 2026!
        </p>

        <div className="bg-slate-50 dark:bg-slate-800/60 rounded-2xl p-4 mb-6 border border-slate-100 dark:border-slate-800 text-left space-y-2">
          <div className="flex items-center text-xs font-semibold text-slate-700 dark:text-slate-200">
            <Sparkles className="w-4 h-4 text-amber-500 mr-2" />
            <span>Planned Features:</span>
          </div>
          <ul className="text-[11px] text-slate-500 dark:text-slate-400 space-y-1 pl-6 list-disc">
            <li>Adaptive LLM Quiz Evaluation</li>
            <li>Hands-on Cloud Sandbox Environment</li>
            <li>Real-world Industry Capstone Projects</li>
          </ul>
        </div>

        <div className="flex space-x-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-all"
          >
            Close
          </button>
          <button
            onClick={handleNotifyMe}
            className="flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white shadow-md shadow-brand-500/20 flex items-center justify-center space-x-1.5 transition-all"
          >
            <BellRing className="w-4 h-4" />
            <span>Notify Me</span>
          </button>
        </div>
      </div>
    </div>
  );
};
