import React, { useState } from 'react';
import {
  User,
  School,
  Mail,
  Flame,
  Award,
  Sparkles,
  Edit,
  Download,
  ShieldCheck,
  MapPin,
  TrendingUp,
  LogOut
} from 'lucide-react';
import { useLearning } from '../../context/LearningContext';
import { EditProfileModal } from '../../components/modals/EditProfileModal';
import { CertificateModal } from '../../components/modals/CertificateModal';

export const ProfilePage = ({ navigateTo }) => {
  const { profile, logout } = useLearning();
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedCert, setSelectedCert] = useState(null);

  return (
    <div className="space-y-8 animate-in fade-in duration-300 max-w-5xl mx-auto">
      {/* User Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950 to-brand-950 text-white p-6 sm:p-8 border border-slate-800 shadow-2xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 z-10 relative">
          <div className="flex items-center space-x-5">
            <img
              src={profile.avatar}
              alt={profile.name}
              className="w-20 h-20 sm:w-24 sm:h-24 rounded-3xl object-cover ring-4 ring-brand-500/40 shadow-xl"
            />
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl sm:text-2xl font-black">{profile.name}</h1>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-500 text-white">
                  Student
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 flex items-center">
                <School className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {profile.college}
              </p>
              <p className="text-xs text-slate-400 mt-0.5 flex items-center">
                <Mail className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {profile.email}
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowEditModal(true)}
            className="py-2.5 px-4 rounded-xl text-xs font-bold bg-white/10 hover:bg-white/20 border border-white/20 text-white flex items-center space-x-1.5 transition-all"
          >
            <Edit className="w-4 h-4" />
            <span>Edit Profile</span>
          </button>
        </div>
      </div>

      {/* Stats Cards Grid (XP Level, Streak, Roadmap Progress) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* XP Level */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">XP Rank & Level</span>
            <Sparkles className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900 dark:text-white">
              {profile.xpLevel} XP
            </div>
            <p className="text-xs font-bold text-brand-600 dark:text-brand-400 mt-0.5">
              {profile.levelTitle}
            </p>
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-brand-500 to-indigo-600 h-full rounded-full"
              style={{ width: `${(profile.xpLevel / profile.nextLevelXp) * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Streak */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Learning Streak</span>
            <Flame className="w-5 h-5 text-amber-500 fill-amber-500" />
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900 dark:text-white">
              {profile.streakDays} Days 🔥
            </div>
            <p className="text-xs font-bold text-amber-600 dark:text-amber-400 mt-0.5">
              Top 5% Daily Consistency
            </p>
          </div>
          <p className="text-[11px] text-slate-400">Keep learning daily to earn +100 XP bonus!</p>
        </div>

        {/* Current Roadmap Progress */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Current Domain</span>
            <TrendingUp className="w-5 h-5 text-emerald-500" />
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900 dark:text-white">
              {profile.roadmapCompletion}%
            </div>
            <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
              {profile.currentDomain}
            </p>
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full"
              style={{ width: `${profile.roadmapCompletion}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Verified Certificates Section */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center uppercase tracking-wider">
            <Award className="w-4 h-4 mr-2 text-amber-500" />
            Verified Certificates ({profile.certificates.length})
          </h2>
          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center">
            <ShieldCheck className="w-4 h-4 mr-1" />
            Authentic Credentials
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {profile.certificates.map((cert) => (
            <div
              key={cert.id}
              onClick={() => setSelectedCert(cert)}
              className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 hover:border-brand-500 transition-all cursor-pointer flex items-center justify-between group"
            >
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center border border-amber-500/30 flex-shrink-0">
                  <Award className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                    {cert.title}
                  </h4>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">Issued: {cert.date}</p>
                  <span className="text-[10px] font-mono text-slate-400">ID: {cert.credentialId}</span>
                </div>
              </div>

              <Download className="w-4 h-4 text-slate-400 group-hover:text-brand-500 transition-colors" />
            </div>
          ))}
        </div>
      </div>

      {/* Account Settings & Sign Out Footer */}
      <div className="pt-4 flex items-center justify-between border-t border-slate-200 dark:border-slate-800">
        <p className="text-xs text-slate-400">Connected account: {profile.email}</p>

        <button
          onClick={() => {
            logout();
            navigateTo('/login');
          }}
          className="px-4 py-2.5 rounded-xl text-xs font-bold bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 hover:bg-rose-100 border border-rose-200 dark:border-rose-900/40 flex items-center space-x-1.5 transition-all"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>

      {/* Modals */}
      <EditProfileModal isOpen={showEditModal} onClose={() => setShowEditModal(false)} />
      <CertificateModal cert={selectedCert} onClose={() => setSelectedCert(null)} />
    </div>
  );
};
