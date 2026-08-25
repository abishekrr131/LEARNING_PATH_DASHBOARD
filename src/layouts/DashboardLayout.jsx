import React from 'react';
import { Navbar } from '../components/navbar/Navbar';
import { Sidebar } from '../components/sidebar/Sidebar';
import { Breadcrumbs } from '../components/common/Breadcrumbs';
import { Toast } from '../components/common/Toast';

export const DashboardLayout = ({ currentPath, navigateTo, children }) => {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col transition-colors duration-200">
      <Navbar navigateTo={navigateTo} />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <Sidebar currentPath={currentPath} navigateTo={navigateTo} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-full">
          <Breadcrumbs path={currentPath} />
          {children}
        </main>
      </div>

      <Toast />
    </div>
  );
};
