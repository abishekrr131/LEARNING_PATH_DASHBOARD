import React from 'react';
import { ChevronRight, Home } from 'lucide-react';

export const Breadcrumbs = ({ path }) => {
  const segments = path.split('/').filter(Boolean);

  const formatSegment = (seg) => {
    if (!seg) return 'Home';
    return seg
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <nav className="flex items-center text-xs font-medium text-slate-500 dark:text-slate-400 space-x-1.5 mb-6">
      <div className="flex items-center hover:text-slate-800 dark:hover:text-slate-200 transition-colors">
        <Home className="w-3.5 h-3.5 mr-1 text-slate-400" />
        <span>Home</span>
      </div>
      {segments.map((seg, idx) => {
        const isLast = idx === segments.length - 1;
        return (
          <React.Fragment key={seg}>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" />
            <span
              className={
                isLast
                  ? 'text-brand-600 dark:text-brand-400 font-semibold'
                  : 'hover:text-slate-800 dark:hover:text-slate-200 transition-colors'
              }
            >
              {formatSegment(seg)}
            </span>
          </React.Fragment>
        );
      })}
    </nav>
  );
};
