import React, { useState, useEffect } from "react";
import MainLayout from "../layouts/MainLayout";
import { profileApi, targetApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function SettingsProfile() {
  const { profile, refreshProfile, logout } = useAuth();

  const [targets, setTargets] = useState([]);
  const [targetId, setTargetId] = useState(profile?.target_id || 1);
  const [level, setLevel] = useState(profile?.current_level || "beginner");
  const [examDate, setExamDate] = useState(profile?.target_exam_date || "");
  const [studyHours, setStudyHours] = useState(profile?.daily_study_hours || 2);
  const [trialConsent, setTrialConsent] = useState(profile?.trial_consent || false);

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    targetApi.list().then((res) => {
      setTargets(res || []);
    });
  }, []);

  useEffect(() => {
    if (profile) {
      setTargetId(profile.target_id || 1);
      setLevel(profile.current_level || "beginner");
      setExamDate(profile.target_exam_date || "");
      setStudyHours(profile.daily_study_hours || 2);
      setTrialConsent(profile.trial_consent || false);
    }
  }, [profile]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    try {
      await profileApi.update({
        target_id: parseInt(targetId),
        current_level: level,
        target_exam_date: examDate || null,
        daily_study_hours: parseFloat(studyHours),
        trial_consent: trialConsent,
      });
      await refreshProfile();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert("Failed to update profile: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleExportData = async () => {
    setExporting(true);
    try {
      const data = await profileApi.export();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `rct_gat_telemetry_export_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to export data: " + err.message);
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== "DELETE") {
      alert("Please type 'DELETE' to confirm.");
      return;
    }
    setDeleting(true);
    try {
      await profileApi.delete();
      logout();
    } catch (err) {
      alert("Failed to delete account: " + err.message);
      setDeleting(false);
    }
  };

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
            Learner Settings &amp; Data Rights
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Configure your curriculum targets, examination timetable, research trial participation, and GDPR data rights.
          </p>
        </div>

        {/* Profile Settings Form */}
        <form
          onSubmit={handleSave}
          className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6"
        >
          <h2 className="text-lg font-bold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
            Learning Profile &amp; Target
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5">
                Career / Exam Target
              </label>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-purple-500 outline-none"
              >
                {targets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.category === "it_career" ? "IT / Software" : "Government Exam"})
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1.5 flex items-center gap-1 font-medium">
                ⚠️ Changing your target shifts active study focus; roadmap and diagnostic progress are tracked independently per curriculum target.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5">
                Current Level
              </label>
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-purple-500 outline-none"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5">
                Target Exam Date (for Urgency F14)
              </label>
              <input
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5">
                Daily Study Hours ({studyHours} hrs/day)
              </label>
              <input
                type="range"
                min="0.5"
                max="8"
                step="0.5"
                value={studyHours}
                onChange={(e) => setStudyHours(e.target.value)}
                className="w-full accent-purple-600 mt-2"
              />
              <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                <span>0.5h</span>
                <span>4.0h</span>
                <span>8.0h</span>
              </div>
            </div>
          </div>

          {/* Research Trial Consent Toggle */}
          <div className="p-4 rounded-2xl bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/40 flex items-start space-x-3.5">
            <input
              type="checkbox"
              id="trialConsent"
              checked={trialConsent}
              onChange={(e) => setTrialConsent(e.target.checked)}
              className="mt-1 w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-gray-300 dark:border-gray-700"
            />
            <label htmlFor="trialConsent" className="text-xs text-gray-700 dark:text-gray-300">
              <span className="font-bold text-purple-900 dark:text-purple-200 block">
                Educational Trial Research Consent
              </span>
              I agree to participate in the anonymized randomized controlled trial (RCT) evaluating GAT attention prerequisite intervention effectiveness vs. standard sequential curriculum navigation.
            </label>
          </div>

          <div className="flex items-center justify-between pt-2">
            {saveSuccess && (
              <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                ✓ Preferences updated successfully
              </span>
            )}
            <div className="ml-auto">
              <button
                type="submit"
                disabled={saving}
                className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-500/20 transition-all"
              >
                {saving ? "Saving Changes…" : "Save Changes"}
              </button>
            </div>
          </div>
        </form>

        {/* Data Rights & Privacy Section */}
        <div className="p-6 sm:p-8 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
            Data Rights &amp; Privacy (GDPR)
          </h2>

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
              <div>
                <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                  Export Learner Telemetry Data
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Download a machine-readable JSON archive containing all logged millisecond assessment responses, mastery records, and AI interactions.
                </p>
              </div>
              <button
                type="button"
                disabled={exporting}
                onClick={handleExportData}
                className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold transition-all shrink-0"
              >
                {exporting ? "Preparing Export…" : "Export JSON 📥"}
              </button>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/40">
              <div>
                <h3 className="font-bold text-sm text-rose-900 dark:text-rose-200">
                  Delete Account &amp; Historical Data
                </h3>
                <p className="text-xs text-rose-700/80 dark:text-rose-400 mt-0.5">
                  Permanently erase your user profile, all diagnostic interaction logs, and derived model mastery vectors. This action cannot be reversed.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowDeleteModal(true)}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all shrink-0"
              >
                Delete Account
              </button>
            </div>
          </div>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteModal && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white dark:bg-gray-900 rounded-3xl p-6 sm:p-8 max-w-md w-full border border-rose-200 dark:border-rose-900 shadow-2xl space-y-4">
              <h3 className="text-lg font-bold text-rose-600 dark:text-rose-400">
                Confirm Irreversible Account Deletion
              </h3>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                This will immediately purge all your response logs, test telemetry, GAT attention history, and profile records from the database.
              </p>
              <div>
                <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1">
                  Type <span className="font-mono text-rose-600">DELETE</span> to confirm:
                </label>
                <input
                  type="text"
                  value={deleteConfirmation}
                  onChange={(e) => setDeleteConfirmation(e.target.value)}
                  placeholder="DELETE"
                  className="w-full px-3.5 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm font-mono text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-rose-500"
                />
              </div>

              <div className="flex items-center space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(false)}
                  className="w-1/2 py-2.5 border border-gray-200 dark:border-gray-800 rounded-xl text-xs font-semibold text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={deleteConfirmation !== "DELETE" || deleting}
                  onClick={handleDeleteAccount}
                  className="w-1/2 py-2.5 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-colors"
                >
                  {deleting ? "Deleting…" : "Confirm Delete"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
