import React from 'react';
import { LoginPage } from '../pages/login';
import { HomePage } from '../pages/home';
import { OnboardingPage } from '../pages/onboarding';
import { AssessmentPage } from '../pages/assessment';
import { AssessmentResultPage } from '../pages/assessment-result';
import { LearningPathPage } from '../pages/learning-path';
import { ProgressPage } from '../pages/progress';
import { ResourcesPage } from '../pages/resources';
import { ProfilePage } from '../pages/profile';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { useLearning } from '../context/LearningContext';

export const AppRouter = () => {
  const { activePath, setActivePath, isAuthenticated } = useLearning();

  const navigateTo = (path) => {
    setActivePath(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // If user is not authenticated or explicitly on login page, render Login view without dashboard shell
  if (!isAuthenticated || activePath === '/login') {
    return <LoginPage navigateTo={navigateTo} />;
  }

  // Render Dashboard Layout wrapper with active route view inside
  const renderPageView = () => {
    switch (activePath) {
      case '/home':
        return <HomePage navigateTo={navigateTo} />;
      case '/onboarding':
        return <OnboardingPage navigateTo={navigateTo} />;
      case '/assessment':
        return <AssessmentPage navigateTo={navigateTo} />;
      case '/assessment-result':
        return <AssessmentResultPage navigateTo={navigateTo} />;
      case '/learning-path':
        return <LearningPathPage navigateTo={navigateTo} />;
      case '/progress':
        return <ProgressPage navigateTo={navigateTo} />;
      case '/resources':
        return <ResourcesPage navigateTo={navigateTo} />;
      case '/profile':
        return <ProfilePage navigateTo={navigateTo} />;
      default:
        return <HomePage navigateTo={navigateTo} />;
    }
  };

  return (
    <DashboardLayout currentPath={activePath} navigateTo={navigateTo}>
      {renderPageView()}
    </DashboardLayout>
  );
};
