import React, { useState } from 'react';
import { Sparkles, Mail, Lock, ArrowRight, ShieldCheck, Zap } from 'lucide-react';
import { useLearning } from '../../context/LearningContext';
import { ThemeToggle } from '../../components/common/ThemeToggle';

export const LoginPage = ({ navigateTo }) => {
  const { login } = useLearning();
  const [email, setEmail] = useState('alex.rivera@stanford.edu');
  const [password, setPassword] = useState('••••••••••••');
  const [rememberMe, setRememberMe] = useState(true);

  const handleSubmit = (e) => {
    e.preventDefault();
    login();
    navigateTo('/home');
  };

  const handleDemoAccess = () => {
    login();
    navigateTo('/home');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 text-slate-100 flex flex-col justify-between p-4 sm:p-6 relative overflow-hidden selection:bg-brand-500 selection:text-white">
      {/* Abstract Glowing Background Shapes */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-500/20 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute top-1/2 -right-40 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-purple-500/15 rounded-full blur-3xl pointer-events-none"></div>

      {/* Header Bar */}
      <header className="flex items-center justify-between max-w-6xl w-full mx-auto z-10">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => navigateTo('/home')}>
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-brand-500 via-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-brand-500/30">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <span className="font-extrabold text-xl tracking-tight text-white">
              Pathfinder <span className="text-brand-400 font-black text-xs uppercase px-2 py-0.5 rounded bg-brand-950/80 border border-brand-800">AI</span>
            </span>
          </div>
        </div>

        <ThemeToggle />
      </header>

      {/* Main Login Card Container */}
      <main className="flex-1 flex items-center justify-center max-w-md w-full mx-auto my-8 z-10">
        <div className="w-full bg-slate-900/80 backdrop-blur-xl border border-slate-800/90 rounded-3xl p-8 shadow-2xl relative">
          <div className="text-center mb-8">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-brand-950/70 text-brand-400 border border-brand-800 text-xs font-semibold mb-3">
              <Zap className="w-3.5 h-3.5" />
              <span>Next-Gen AI Learning Platform</span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Welcome Back</h1>
            <p className="text-xs text-slate-400 mt-1.5">
              Enter your credentials to access your personalized learning path dashboard.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="name@university.edu"
                  className="w-full pl-10 pr-4 py-2.5 text-xs bg-slate-800/90 border border-slate-700/80 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 text-white placeholder-slate-500 transition-all"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300">Password</label>
                <a
                  href="#forgot"
                  onClick={(e) => {
                    e.preventDefault();
                    alert('Password reset link has been sent to your registered email.');
                  }}
                  className="text-[11px] font-semibold text-brand-400 hover:text-brand-300 transition-colors"
                >
                  Forgot Password?
                </a>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 text-xs bg-slate-800/90 border border-slate-700/80 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 text-white placeholder-slate-500 transition-all"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center space-x-2 cursor-pointer text-xs text-slate-400 select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-brand-500 focus:ring-brand-500/30"
                />
                <span>Remember me for 30 days</span>
              </label>
            </div>

            <button
              type="submit"
              className="w-full py-3 px-4 rounded-xl text-xs font-bold bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-500 hover:from-brand-500 hover:to-indigo-500 text-white shadow-lg shadow-brand-500/25 flex items-center justify-center space-x-2 transition-all"
            >
              <span>Sign In to Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800"></div>
            </div>
            <span className="relative px-3 bg-slate-900 text-[10px] font-semibold text-slate-500 uppercase">
              Or Instant Access
            </span>
          </div>

          <button
            onClick={handleDemoAccess}
            type="button"
            className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/70 hover:bg-slate-800 border border-slate-700/70 transition-all flex items-center justify-center space-x-2"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Continue as Demo Student</span>
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center text-[11px] text-slate-500 max-w-6xl w-full mx-auto z-10">
        <p>© 2026 Pathfinder AI Learning System. College Major Project Demo.</p>
      </footer>
    </div>
  );
};
