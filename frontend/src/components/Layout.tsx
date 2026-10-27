import React from 'react';
import { Navbar } from './Navbar';

interface Props {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Layout: React.FC<Props> = ({ children, activeTab, setActiveTab }) => {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};
