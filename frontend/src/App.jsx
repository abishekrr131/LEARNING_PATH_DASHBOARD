import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";

// Pages
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import AssessmentInstructions from "./pages/AssessmentInstructions";
import DiagnosticRunner from "./pages/DiagnosticRunner";
import VerificationRunner from "./pages/VerificationRunner";
import FollowUpRunner from "./pages/FollowUpRunner";
import AssessmentResult from "./pages/AssessmentResult";
import AIAnalysis from "./pages/AIAnalysis";
import Dashboard from "./pages/Dashboard";
import WeakTopics from "./pages/WeakTopics";
import RootCauseAnalysis from "./pages/RootCauseAnalysis";
import LearningPath from "./pages/LearningPath";
import Resources from "./pages/Resources";
import StudySchedule from "./pages/StudySchedule";
import PracticeMode from "./pages/PracticeMode";
import AssessmentsHub from "./pages/AssessmentsHub";
import SpecialTestRunnerPage from "./pages/SpecialTestRunnerPage";
import ProgressReadiness from "./pages/ProgressReadiness";
import SettingsProfile from "./pages/SettingsProfile";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading, profile } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center">
        <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">Loading Learner Session…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />

            {/* Onboarding */}
            <Route
              path="/onboarding"
              element={
                <ProtectedRoute>
                  <Onboarding />
                </ProtectedRoute>
              }
            />

            {/* Dashboard & Core Analytics */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/weak-topics"
              element={
                <ProtectedRoute>
                  <WeakTopics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/root-cause"
              element={
                <ProtectedRoute>
                  <RootCauseAnalysis />
                </ProtectedRoute>
              }
            />
            <Route
              path="/progress"
              element={
                <ProtectedRoute>
                  <ProgressReadiness />
                </ProtectedRoute>
              }
            />

            {/* Curriculum & Resources */}
            <Route
              path="/learning-path"
              element={
                <ProtectedRoute>
                  <LearningPath />
                </ProtectedRoute>
              }
            />
            <Route
              path="/resources"
              element={
                <ProtectedRoute>
                  <Resources />
                </ProtectedRoute>
              }
            />
            <Route
              path="/schedule"
              element={
                <ProtectedRoute>
                  <StudySchedule />
                </ProtectedRoute>
              }
            />

            {/* Assessments Suite */}
            <Route
              path="/assessments"
              element={
                <ProtectedRoute>
                  <AssessmentsHub />
                </ProtectedRoute>
              }
            />
            <Route
              path="/diagnostic/instructions"
              element={
                <ProtectedRoute>
                  <AssessmentInstructions />
                </ProtectedRoute>
              }
            />
            <Route
              path="/diagnostic/run"
              element={
                <ProtectedRoute>
                  <DiagnosticRunner />
                </ProtectedRoute>
              }
            />
            <Route
              path="/special-test"
              element={
                <ProtectedRoute>
                  <SpecialTestRunnerPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/verification"
              element={
                <ProtectedRoute>
                  <VerificationRunner />
                </ProtectedRoute>
              }
            />
            <Route
              path="/followup"
              element={
                <ProtectedRoute>
                  <FollowUpRunner />
                </ProtectedRoute>
              }
            />
            <Route
              path="/practice"
              element={
                <ProtectedRoute>
                  <PracticeMode />
                </ProtectedRoute>
              }
            />

            {/* Results & AI Analysis */}
            <Route
              path="/result/:id"
              element={
                <ProtectedRoute>
                  <AssessmentResult />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ai-analysis"
              element={
                <ProtectedRoute>
                  <AIAnalysis />
                </ProtectedRoute>
              }
            />

            {/* Settings & GDPR Data Rights */}
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <SettingsProfile />
                </ProtectedRoute>
              }
            />

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
