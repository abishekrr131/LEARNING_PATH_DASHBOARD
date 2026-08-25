import React, { useState } from 'react';
import {
  Code2,
  Cpu,
  Cloud,
  Database,
  ShieldCheck,
  Search,
  Sparkles,
  ArrowRight,
  BookOpen,
  Star,
  CheckCircle2
} from 'lucide-react';
import { DOMAINS } from '../../data/dummyData';
import { useLearning } from '../../context/LearningContext';
import { ComingSoonModal } from '../../components/modals/ComingSoonModal';

export const HomePage = ({ navigateTo }) => {
  const { searchQuery, setSearchQuery, setCurrentDomain } = useLearning();
  const [selectedComingSoon, setSelectedComingSoon] = useState(null);

  const iconMap = {
    Code2: Code2,
    Cpu: Cpu,
    Cloud: Cloud,
    Database: Database,
    ShieldCheck: ShieldCheck
  };

  // Filter 5 domains based on global or local search
  const filteredDomains = DOMAINS.filter(
    (d) =>
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleDomainClick = (domain) => {
    if (domain.id === 'full-stack') {
      setCurrentDomain('full-stack');
      navigateTo('/onboarding');
    } else {
      setSelectedComingSoon(domain);
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-brand-900 via-indigo-900 to-slate-900 text-white p-6 sm:p-8 border border-slate-800 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-80 h-80 bg-brand-500/20 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-brand-500/20 border border-brand-400/30 text-brand-300 text-xs font-semibold mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Driven Learning Experience</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Which discipline do you want to master today?
          </h1>

          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Select a domain below. Our AI system will evaluate your current skill level, build a personalized adaptive roadmap, and provide interactive assessments.
          </p>
        </div>

        {/* Hero Search Bar */}
        <div className="mt-6 relative max-w-lg">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search domains (e.g., Full Stack, Machine Learning)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-xs bg-white/10 backdrop-blur-md border border-white/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-400 text-white placeholder-slate-400 transition-all"
          />
        </div>
      </div>

      {/* Domain Cards Section Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
            Explore Learning Domains
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Showing {filteredDomains.length} curated engineering disciplines
          </p>
        </div>
      </div>

      {/* Responsive Grid of 5 Domains (Wrap nicely into 2-3 columns, NOT stacked vertically) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredDomains.map((domain) => {
          const IconComponent = iconMap[domain.iconName] || Code2;
          const isFullStack = domain.id === 'full-stack';

          return (
            <div
              key={domain.id}
              onClick={() => handleDomainClick(domain)}
              className={`group relative rounded-3xl p-6 transition-all duration-300 cursor-pointer flex flex-col justify-between border ${
                isFullStack
                  ? 'bg-gradient-to-b from-white to-brand-50/40 dark:from-slate-900 dark:to-brand-950/20 border-brand-500/40 dark:border-brand-500/40 shadow-xl shadow-brand-500/10 hover:shadow-2xl hover:shadow-brand-500/20 hover:-translate-y-1'
                  : 'bg-white dark:bg-slate-900 border-slate-200/90 dark:border-slate-800 shadow-sm hover:shadow-xl hover:border-slate-300 dark:hover:border-slate-700 hover:-translate-y-1'
              }`}
            >
              <div>
                {/* Top Badge & Icon */}
                <div className="flex items-center justify-between mb-4">
                  <div
                    className={`w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-md bg-gradient-to-tr ${domain.color}`}
                  >
                    <IconComponent className="w-6 h-6" />
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 flex items-center">
                      <BookOpen className="w-3 h-3 mr-1 text-brand-500" />
                      {domain.coursesCount} Courses
                    </span>
                  </div>
                </div>

                {/* Title & Category */}
                <span className="text-[10px] uppercase font-bold text-brand-600 dark:text-brand-400 tracking-wider">
                  {domain.category}
                </span>
                <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                  {domain.title}
                </h3>

                <p className="text-xs text-slate-600 dark:text-slate-400 mt-2 line-clamp-3 leading-relaxed">
                  {domain.description}
                </p>

                {/* Skill Pills */}
                <div className="flex flex-wrap gap-1.5 mt-4">
                  {domain.skills.map((skill) => (
                    <span
                      key={skill}
                      className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200/60 dark:border-slate-700/60"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Bottom Action Footer */}
              <div className="pt-6 mt-6 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center">
                  <Star className="w-3 h-3 text-amber-400 fill-amber-400 mr-1" />
                  {domain.popularity}
                </span>

                <button
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                    isFullStack
                      ? 'bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 group-hover:bg-slate-200 dark:group-hover:bg-slate-700'
                  }`}
                >
                  <span>{isFullStack ? 'Explore Path' : 'Preview'}</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Coming Soon Modal */}
      <ComingSoonModal
        domain={selectedComingSoon}
        onClose={() => setSelectedComingSoon(null)}
      />
    </div>
  );
};
