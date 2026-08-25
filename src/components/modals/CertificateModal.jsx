import React from 'react';
import { X, Award, Download, CheckCircle2, ShieldCheck, ExternalLink } from 'lucide-react';
import { useLearning } from '../../context/LearningContext';

export const CertificateModal = ({ cert, onClose }) => {
  const { profile, showToast } = useLearning();

  if (!cert) return null;

  const handleDownload = () => {
    showToast(`Downloading ${cert.title} PDF Certificate...`, 'success');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl max-w-xl w-full p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Certificate Display Card */}
        <div className="border-4 border-double border-brand-500/30 rounded-2xl p-6 bg-gradient-to-br from-slate-50 via-white to-brand-50/30 dark:from-slate-900 dark:via-slate-850 dark:to-slate-800 text-center relative overflow-hidden my-2 shadow-inner">
          <div className="flex justify-center mb-3">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center border border-amber-500/30">
              <Award className="w-7 h-7" />
            </div>
          </div>

          <span className="text-[10px] uppercase tracking-widest font-extrabold text-brand-600 dark:text-brand-400">
            Certificate of Completion
          </span>

          <h3 className="text-xl font-black text-slate-900 dark:text-white mt-2 mb-1">
            {cert.title}
          </h3>

          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            This certifies that <strong className="text-slate-800 dark:text-slate-200">{profile.name}</strong> from {profile.college} has successfully demonstrated mastery in {cert.title}.
          </p>

          <div className="flex items-center justify-between text-[11px] text-slate-400 pt-4 border-t border-slate-200/80 dark:border-slate-800">
            <div>
              <p className="font-semibold text-slate-700 dark:text-slate-300">Issued Date</p>
              <span>{cert.date}</span>
            </div>
            <div className="flex items-center text-emerald-600 dark:text-emerald-400 font-bold">
              <ShieldCheck className="w-4 h-4 mr-1" />
              <span>Verified Credentials</span>
            </div>
            <div>
              <p className="font-semibold text-slate-700 dark:text-slate-300">Credential ID</p>
              <span>{cert.credentialId}</span>
            </div>
          </div>
        </div>

        <div className="flex space-x-3 mt-4">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-all"
          >
            Close
          </button>
          <button
            onClick={handleDownload}
            className="flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20 flex items-center justify-center space-x-2 transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Download PDF</span>
          </button>
        </div>
      </div>
    </div>
  );
};
