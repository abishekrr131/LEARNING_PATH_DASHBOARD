import React, { useState, useEffect } from 'react';
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  Award,
  Sparkles,
  HelpCircle
} from 'lucide-react';
import { SAMPLE_QUESTIONS_20, SAMPLE_QUESTIONS_40 } from '../../data/dummyData';
import { useLearning } from '../../context/LearningContext';

export const AssessmentPage = ({ navigateTo }) => {
  const { onboardingData, submitAssessment, showToast } = useLearning();

  const questions =
    onboardingData.questionsCount === 40 ? SAMPLE_QUESTIONS_40 : SAMPLE_QUESTIONS_20;

  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(questions.length * 45); // 45 seconds per question

  // Timer countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins}:${s < 10 ? '0' : ''}${s}`;
  };

  const handleSelectOption = (optionIndex) => {
    const currentQ = questions[currentIndex];
    setUserAnswers((prev) => ({
      ...prev,
      [currentQ.id]: optionIndex
    }));
  };

  const handleSubmit = () => {
    submitAssessment(userAnswers, questions);
    showToast('Assessment submitted successfully!', 'success');
    navigateTo('/assessment-result');
  };

  const currentQ = questions[currentIndex];
  const progressPercent = Math.round(((currentIndex + 1) / questions.length) * 100);
  const answeredCount = Object.keys(userAnswers).length;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Top Bar Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-extrabold uppercase tracking-wider text-brand-600 dark:text-brand-400">
              Full Stack Initial Placement Test
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-50 text-brand-600 dark:bg-brand-950/60 dark:text-brand-400 border border-brand-200 dark:border-brand-800">
              {questions.length} Questions
            </span>
          </div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white mt-1">
            Topic Diagnostic Evaluation
          </h1>
        </div>

        {/* Timer Box */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-3.5 py-2 bg-slate-900 text-white dark:bg-slate-800 rounded-2xl border border-slate-700 shadow-md">
            <Clock className="w-4 h-4 text-amber-400 animate-pulse" />
            <span className="text-xs font-mono font-bold tracking-wider">
              {formatTime(timeLeft)}
            </span>
          </div>

          <button
            onClick={handleSubmit}
            className="py-2 px-4 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20"
          >
            Submit Quiz
          </button>
        </div>
      </div>

      {/* Progress Bar & Question Navigator */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
          <span>Question {currentIndex + 1} of {questions.length}</span>
          <span>{answeredCount} of {questions.length} Answered</span>
        </div>

        {/* Progress Line */}
        <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-brand-500 to-indigo-600 h-full rounded-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          ></div>
        </div>

        {/* Question Grid Bubbles */}
        <div className="flex flex-wrap gap-1.5 pt-2 max-h-24 overflow-y-auto">
          {questions.map((q, idx) => {
            const isAnswered = userAnswers[q.id] !== undefined;
            const isCurrent = idx === currentIndex;
            return (
              <button
                key={q.id}
                onClick={() => setCurrentIndex(idx)}
                className={`w-7 h-7 rounded-lg text-[11px] font-bold transition-all flex items-center justify-center ${
                  isCurrent
                    ? 'bg-brand-600 text-white ring-2 ring-brand-500/40 shadow-md'
                    : isAnswered
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700'
                }`}
              >
                {idx + 1}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Question Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800">
            {currentQ.topic}
          </span>
          <span className="text-xs font-medium text-slate-400">
            Question #{currentQ.id}
          </span>
        </div>

        <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white leading-relaxed">
          {currentQ.question}
        </h2>

        {/* Options List */}
        <div className="space-y-3 pt-2">
          {currentQ.options.map((opt, optIdx) => {
            const isSelected = userAnswers[currentQ.id] === optIdx;
            const labels = ['A', 'B', 'C', 'D'];

            return (
              <div
                key={optIdx}
                onClick={() => handleSelectOption(optIdx)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center space-x-4 ${
                  isSelected
                    ? 'bg-brand-50/80 dark:bg-brand-950/50 border-brand-500 ring-2 ring-brand-500/20 shadow-md'
                    : 'bg-slate-50/60 dark:bg-slate-800/40 border-slate-200/80 dark:border-slate-700/60 hover:border-slate-300 dark:hover:border-slate-600'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-xl font-extrabold text-xs flex items-center justify-center flex-shrink-0 transition-colors ${
                    isSelected
                      ? 'bg-brand-500 text-white shadow-md'
                      : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                  }`}
                >
                  {labels[optIdx]}
                </div>

                <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-relaxed">
                  {opt}
                </span>
              </div>
            );
          })}
        </div>

        {/* Bottom Pagination Controls */}
        <div className="pt-6 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <button
            onClick={() => setCurrentIndex((prev) => Math.max(prev - 1, 0))}
            disabled={currentIndex === 0}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 transition-all flex items-center space-x-1.5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          {currentIndex === questions.length - 1 ? (
            <button
              onClick={handleSubmit}
              className="px-6 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/20 flex items-center space-x-2 transition-all"
            >
              <span>Finish & Submit</span>
              <CheckCircle2 className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => setCurrentIndex((prev) => Math.min(prev + 1, questions.length - 1))}
              className="px-6 py-2.5 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20 flex items-center space-x-2 transition-all"
            >
              <span>Next Question</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
