import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import { useLearning } from '../../context/LearningContext';

export const Toast = () => {
  const { toast } = useLearning();

  if (!toast) return null;

  const icons = {
    success: <CheckCircle2 className="w-4 h-4 text-emerald-500" />,
    error: <AlertCircle className="w-4 h-4 text-rose-500" />,
    info: <Info className="w-4 h-4 text-brand-500" />
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center space-x-3 px-4 py-3 bg-slate-900 text-white dark:bg-slate-800 dark:text-slate-100 rounded-xl shadow-xl border border-slate-700/50 text-sm animate-bounce-short">
      {icons[toast.type] || icons.info}
      <span>{toast.message}</span>
    </div>
  );
};
