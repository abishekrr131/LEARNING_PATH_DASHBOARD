import React, { createContext, useContext, useState } from 'react';
import { ROADMAP_NODES, USER_PROFILE, ASSESSMENT_HISTORY_DATA } from '../data/dummyData';

const LearningContext = createContext();

export const LearningProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(true);
  const [currentDomain, setCurrentDomain] = useState('full-stack');
  const [activePath, setActivePath] = useState('/home');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Onboarding state
  const [onboardingData, setOnboardingData] = useState({
    experienceLevel: 'intermediate', // beginner, intermediate, advanced
    selectedTopics: ['html', 'css', 'javascript'],
    questionsCount: 20
  });

  // Assessment results state
  const [assessmentResult, setAssessmentResult] = useState({
    score: 85,
    accuracy: 88,
    totalQuestions: 20,
    correctAnswers: 17,
    masteredSkills: ['HTML5 Syntax', 'CSS Grid', 'ES6 Async/Await', 'React State'],
    weakSkills: ['MongoDB Aggregations', 'Express Middleware Routing'],
    recommendedTopics: ['Node.js Stream Processing', 'Express Error Handlers'],
    readinessScore: 82,
    topicBreakdown: [
      { name: 'HTML5', score: 95 },
      { name: 'CSS3', score: 90 },
      { name: 'JavaScript', score: 85 },
      { name: 'React.js', score: 80 },
      { name: 'Node.js', score: 65 },
      { name: 'Express.js', score: 60 },
      { name: 'MongoDB', score: 55 }
    ]
  });

  // Roadmap Nodes state
  const [roadmap, setRoadmap] = useState(ROADMAP_NODES);

  // History table state
  const [assessmentHistory, setAssessmentHistory] = useState(ASSESSMENT_HISTORY_DATA);

  // Bookmarked Resources
  const [bookmarks, setBookmarks] = useState(['res-1', 'res-7', 'res-16']);

  // User Profile
  const [profile, setProfile] = useState(USER_PROFILE);

  // Toast Notification state
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3500);
  };

  const toggleBookmark = (resId) => {
    setBookmarks((prev) => {
      const exists = prev.includes(resId);
      if (exists) {
        showToast('Resource removed from bookmarks', 'info');
        return prev.filter((id) => id !== resId);
      } else {
        showToast('Resource saved to bookmarks!', 'success');
        return [...prev, resId];
      }
    });
  };

  const submitAssessment = (answers, questions) => {
    let correct = 0;
    questions.forEach((q) => {
      if (answers[q.id] === q.answer) {
        correct += 1;
      }
    });
    const percentage = Math.round((correct / questions.length) * 100);

    const newResult = {
      score: percentage,
      accuracy: Math.min(percentage + 3, 98),
      totalQuestions: questions.length,
      correctAnswers: correct,
      masteredSkills: percentage >= 80 ? ['HTML5 Syntax', 'CSS Grid', 'ES6 Modern Syntax', 'React Component State'] : ['HTML5 Basics', 'CSS Properties'],
      weakSkills: percentage >= 80 ? ['MongoDB Aggregations', 'Express Middleware'] : ['JavaScript Promises', 'Async Execution', 'Node Event Loop'],
      recommendedTopics: percentage >= 80 ? ['Node.js Microservices', 'Advanced Express Auth'] : ['JavaScript Async Deep Dive', 'React Hooks Fundamentals'],
      readinessScore: Math.round(percentage * 0.95),
      topicBreakdown: [
        { name: 'HTML5', score: Math.min(percentage + 10, 100) },
        { name: 'CSS3', score: Math.min(percentage + 5, 98) },
        { name: 'JavaScript', score: percentage },
        { name: 'React.js', score: Math.max(percentage - 5, 40) },
        { name: 'Node.js', score: Math.max(percentage - 15, 30) },
        { name: 'Express.js', score: Math.max(percentage - 20, 25) },
        { name: 'MongoDB', score: Math.max(percentage - 25, 20) }
      ]
    };

    setAssessmentResult(newResult);

    // Update history
    const newEntry = {
      id: `AH-${Date.now().toString().slice(-3)}`,
      name: questions.length === 20 ? 'Full Stack Quick Placement Test' : 'Full Stack Comprehensive Placement Test',
      topic: 'Full Stack',
      date: new Date().toISOString().split('T')[0],
      marks: `${correct}/${questions.length}`,
      percentage,
      timeTaken: '15 mins',
      status: percentage >= 60 ? 'Passed' : 'Failed',
      type: 'Initial Assessment'
    };
    setAssessmentHistory((prev) => [newEntry, ...prev]);

    // Automatically update roadmap completion status based on assessment
    if (percentage >= 75) {
      setRoadmap((prev) =>
        prev.map((node) => {
          if (node.id === 'javascript') return { ...node, status: 'completed', progress: 100 };
          if (node.id === 'react') return { ...node, status: 'in-progress', progress: 50 };
          if (node.id === 'nodejs') return { ...node, status: 'unlocked', progress: 10 };
          return node;
        })
      );
    }
  };

  const login = () => {
    setIsAuthenticated(true);
    showToast('Successfully logged in!', 'success');
  };

  const logout = () => {
    setIsAuthenticated(false);
    showToast('Logged out of session', 'info');
  };

  return (
    <LearningContext.Provider
      value={{
        isAuthenticated,
        login,
        logout,
        currentDomain,
        setCurrentDomain,
        activePath,
        setActivePath,
        searchQuery,
        setSearchQuery,
        onboardingData,
        setOnboardingData,
        assessmentResult,
        setAssessmentResult,
        submitAssessment,
        roadmap,
        setRoadmap,
        assessmentHistory,
        setAssessmentHistory,
        bookmarks,
        toggleBookmark,
        profile,
        setProfile,
        toast,
        showToast
      }}
    >
      {children}
    </LearningContext.Provider>
  );
};

export const useLearning = () => useContext(LearningContext);
