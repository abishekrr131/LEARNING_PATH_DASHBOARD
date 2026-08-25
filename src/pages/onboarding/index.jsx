import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  ArrowRight,
  HelpCircle,
  Code2,
  Layers,
  Zap,
  BookOpen,
  ArrowLeft
} from 'lucide-react';
import { TOPICS } from '../../data/dummyData';
import { useLearning } from '../../context/LearningContext';

export const OnboardingPage = ({ navigateTo }) => {
  const { setOnboardingData, setRoadmap, showToast } = useLearning();

  const [experienceLevel, setExperienceLevel] = useState('intermediate'); // beginner, intermediate, advanced
  const [selectedTopics, setSelectedTopics] = useState(['html', 'css', 'javascript']);

  const handleTopicToggle = (topicId) => {
    setSelectedTopics((prev) =>
      prev.includes(topicId)
        ? prev.filter((id) => id !== topicId)
        : [...prev, topicId]
    );
  };

  const handleContinue = () => {
    const questionsCount = selectedTopics.length <= 3 ? 20 : 40;

    setOnboardingData({
      experienceLevel,
      selectedTopics,
      questionsCount
    });

    if (experienceLevel === 'beginner') {
      showToast('Generated personalized Beginner Full Stack Roadmap!', 'success');
      // Set initial beginner roadmap state
      setRoadmap((prev) =>
        prev.map((node, idx) => {
          if (idx === 0) return { ...node, status: 'in-progress', progress: 20 };
          return { ...node, status: 'locked', progress: 0 };
        })
      );
      navigateTo('/learning-path');
    } else {
      showToast(`Configured ${questionsCount}-Question placement assessment!`, 'info');
      navigateTo('/assessment');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => navigateTo('/home')}
          className="flex items-center space-x-2 text-xs font-semibold text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Home</span>
        </button>

        <span className="text-xs font-bold px-3 py-1 rounded-full bg-brand-50 text-brand-600 dark:bg-brand-950/60 dark:text-brand-400 border border-brand-200 dark:border-brand-800 flex items-center">
          <Sparkles className="w-3.5 h-3.5 mr-1" />
          Onboarding Wizard
        </span>
      </div>

      {/* Hero Title */}
      <div className="text-center space-y-2 py-2">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Personalize Your Full Stack Path
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          Help our AI understand your current experience level to tailor your diagnostic assessment and learning roadmap.
        </p>
      </div>

      {/* Step 1: Experience Level Selection */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center">
          <span className="w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-xs font-black mr-2">
            1
          </span>
          Tell us about your Full Stack experience
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            {
              id: 'beginner',
              title: 'I am completely new',
              desc: 'No coding experience. Start from scratch.',
              badge: 'Zero Experience'
            },
            {
              id: 'intermediate',
              title: 'I know some concepts',
              desc: 'Familiar with HTML/CSS & JS basics.',
              badge: 'Some Experience'
            },
            {
              id: 'advanced',
              title: 'I already have experience',
              desc: 'Built web apps, looking to master stacks.',
              badge: 'Experienced'
            }
          ].map((item) => {
            const isSelected = experienceLevel === item.id;
            return (
              <div
                key={item.id}
                onClick={() => setExperienceLevel(item.id)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'bg-brand-50/70 dark:bg-brand-950/40 border-brand-500 ring-2 ring-brand-500/20 shadow-md'
                    : 'bg-slate-50/60 dark:bg-slate-800/40 border-slate-200/80 dark:border-slate-700/60 hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400">
                      {item.badge}
                    </span>
                    {isSelected && <CheckCircle2 className="w-4 h-4 text-brand-500" />}
                  </div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">{item.title}</h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">{item.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Step 2: Skill Topic Selection (Shown for Intermediate & Advanced) */}
      {experienceLevel !== 'beginner' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center">
              <span className="w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-xs font-black mr-2">
                2
              </span>
              Select topics you are familiar with
            </h2>

            <span className="text-xs font-semibold text-brand-600 dark:text-brand-400">
              {selectedTopics.length} / {TOPICS.length} Selected
            </span>
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400">
            Based on your selection, we will generate a customized diagnostic assessment:
            <strong className="text-slate-700 dark:text-slate-300 ml-1">
              {selectedTopics.length <= 3 ? '20 Questions Test' : '40 Questions Test'}
            </strong>
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            {TOPICS.map((topic) => {
              const isChecked = selectedTopics.includes(topic.id);
              return (
                <div
                  key={topic.id}
                  onClick={() => handleTopicToggle(topic.id)}
                  className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start space-x-3 ${
                    isChecked
                      ? 'bg-brand-50/50 dark:bg-brand-950/30 border-brand-500/80 shadow-sm'
                      : 'bg-slate-50/60 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700/60 opacity-80 hover:opacity-100'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {}}
                    className="w-4 h-4 rounded border-slate-300 text-brand-500 focus:ring-brand-500 mt-0.5"
                  />
                  <div>
                    <h4 className="text-xs font-bold text-slate-900 dark:text-white">{topic.name}</h4>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                      {topic.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Action Footer */}
      <div className="pt-4 flex items-center justify-between">
        <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center">
          <HelpCircle className="w-4 h-4 mr-1.5 text-slate-400" />
          <span>You can retake this diagnostic test at any time.</span>
        </div>

        <button
          onClick={handleContinue}
          className="py-3 px-6 rounded-2xl text-xs font-bold bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-500 hover:from-brand-500 hover:to-indigo-500 text-white shadow-lg shadow-brand-500/25 flex items-center space-x-2 transition-all"
        >
          <span>
            {experienceLevel === 'beginner'
              ? 'Generate Personalized Roadmap'
              : `Start Diagnostic Test (${selectedTopics.length <= 3 ? '20 Qs' : '40 Qs'})`}
          </span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
