import React from 'react';
import { ThemeProvider } from '../context/ThemeContext';
import { LearningProvider } from '../context/LearningContext';
import { AppRouter } from '../routes';

export function App() {
  return (
    <ThemeProvider>
      <LearningProvider>
        <AppRouter />
      </LearningProvider>
    </ThemeProvider>
  );
}

export default App;
