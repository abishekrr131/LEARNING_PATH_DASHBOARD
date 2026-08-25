import React, { useState } from 'react';
import {
  BookOpen,
  Video,
  Code2,
  HelpCircle,
  FileText,
  Bookmark,
  Download,
  Search,
  ExternalLink,
  Sparkles,
  CheckCircle2
} from 'lucide-react';
import { RESOURCES_BY_TECH } from '../../data/dummyData';
import { useLearning } from '../../context/LearningContext';

export const ResourcesPage = () => {
  const { bookmarks, toggleBookmark, showToast } = useLearning();
  const [selectedTech, setSelectedTech] = useState('All');
  const [resourceSearch, setResourceSearch] = useState('');

  const techKeys = Object.keys(RESOURCES_BY_TECH);

  const handleDownloadCheatSheet = (title) => {
    showToast(`Downloading cheat sheet: ${title}`, 'success');
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950 to-brand-950 text-white p-6 sm:p-8 border border-slate-800 shadow-2xl">
        <div className="max-w-2xl z-10 relative">
          <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/30">
            Curated Library
          </span>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-3">
            Full Stack Learning Resources
          </h1>

          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Browse official documentation, video masterclasses, hands-on capstone projects, interactive drills, and downloadable cheat sheets grouped by technology.
          </p>
        </div>

        {/* Search Bar */}
        <div className="mt-6 relative max-w-lg z-10">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search resources (e.g. Flexbox, Async, Mongoose)..."
            value={resourceSearch}
            onChange={(e) => setResourceSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-xs bg-white/10 backdrop-blur-md border border-white/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-400 text-white placeholder-slate-400 transition-all"
          />
        </div>
      </div>

      {/* Technology Filter Chips */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          onClick={() => setSelectedTech('All')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            selectedTech === 'All'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
              : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300'
          }`}
        >
          All Technologies
        </button>

        {techKeys.map((tech) => (
          <button
            key={tech}
            onClick={() => setSelectedTech(tech)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              selectedTech === tech
                ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300'
            }`}
          >
            {tech}
          </button>
        ))}
      </div>

      {/* Resource Sections Grouped by Tech */}
      <div className="space-y-8">
        {techKeys
          .filter((t) => selectedTech === 'All' || selectedTech === t)
          .map((tech) => {
            const items = RESOURCES_BY_TECH[tech].filter(
              (item) =>
                item.title.toLowerCase().includes(resourceSearch.toLowerCase()) ||
                item.desc.toLowerCase().includes(resourceSearch.toLowerCase()) ||
                item.type.toLowerCase().includes(resourceSearch.toLowerCase())
            );

            if (items.length === 0) return null;

            return (
              <div key={tech} className="space-y-4">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-extrabold uppercase tracking-wider text-slate-900 dark:text-white px-3 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                    {tech}
                  </span>
                  <span className="text-xs text-slate-400 font-medium">
                    {items.length} Resources Available
                  </span>
                </div>

                {/* Sub-cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((res) => {
                    const isBookmarked = bookmarks.includes(res.id);

                    const typeIcons = {
                      Documentation: BookOpen,
                      Videos: Video,
                      Projects: Code2,
                      Practice: HelpCircle,
                      'Cheat Sheet': FileText
                    };

                    const IconComponent = typeIcons[res.type] || FileText;

                    return (
                      <div
                        key={res.id}
                        className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm hover:shadow-xl transition-all flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-600 dark:bg-brand-950/60 dark:text-brand-400 border border-brand-200 dark:border-brand-800 flex items-center">
                              <IconComponent className="w-3 h-3 mr-1" />
                              {res.type}
                            </span>

                            <button
                              onClick={() => toggleBookmark(res.id)}
                              className={`p-1.5 rounded-xl border transition-colors ${
                                isBookmarked
                                  ? 'bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800 text-amber-500'
                                  : 'border-slate-200 dark:border-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
                              }`}
                              title={isBookmarked ? 'Bookmarked' : 'Save resource'}
                            >
                              <Bookmark className={`w-3.5 h-3.5 ${isBookmarked ? 'fill-current' : ''}`} />
                            </button>
                          </div>

                          <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-1 leading-snug">
                            {res.title}
                          </h4>

                          <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                            {res.desc}
                          </p>
                        </div>

                        <div className="pt-4 mt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                          <span className="text-[11px] font-semibold text-slate-400">
                            {res.duration}
                          </span>

                          {res.type === 'Cheat Sheet' ? (
                            <button
                              onClick={() => handleDownloadCheatSheet(res.title)}
                              className="px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm flex items-center space-x-1 transition-all"
                            >
                              <Download className="w-3.5 h-3.5" />
                              <span>Download</span>
                            </button>
                          ) : (
                            <a
                              href={res.url}
                              onClick={(e) => {
                                e.preventDefault();
                                showToast(`Opening resource: ${res.title}`, 'info');
                              }}
                              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 flex items-center space-x-1 transition-all"
                            >
                              <span>Explore</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
};
