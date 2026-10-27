import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { SystemStats } from '../types';
import { User, Shield, HardDrive, Cpu, LogOut, CheckCircle2 } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [stats, setStats] = useState<SystemStats | null>(null);

  useEffect(() => {
    api.getStats().then(setStats).catch(console.error);
  }, []);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const maxStorageBytes = 100 * 1024 * 1024; // 100 MB per user
  const usedBytes = stats?.storage_used_bytes || 0;
  const storagePercent = Math.min(Math.round((usedBytes / maxStorageBytes) * 100), 100);

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-150">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Platform Settings</h1>
        <p className="text-xs text-slate-400 mt-1">
          Review your account profile, storage quotas, and RAG pipeline configurations
        </p>
      </div>

      {/* Account Profile Card */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6">
        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <div className="p-2.5 rounded-xl bg-slate-800 text-slate-300">
            <User className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Account Profile</h2>
            <p className="text-xs text-slate-400">Authenticated identity details</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-slate-500 block mb-1">User Identifier (UUID)</span>
            <code className="text-slate-300 font-mono bg-slate-950 px-2 py-1 rounded border border-slate-800 block truncate">
              {user?.id}
            </code>
          </div>
          <div>
            <span className="text-slate-500 block mb-1">Email Address</span>
            <span className="text-slate-200 font-medium">{user?.email}</span>
          </div>
          <div>
            <span className="text-slate-500 block mb-1">Full Name</span>
            <span className="text-slate-200 font-medium">{user?.full_name || 'Not set'}</span>
          </div>
          <div>
            <span className="text-slate-500 block mb-1">Account Status</span>
            <span className="inline-flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Active & Verified
            </span>
          </div>
        </div>
      </div>

      {/* Storage Quota Card */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6">
        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <div className="p-2.5 rounded-xl bg-slate-800 text-slate-300">
            <HardDrive className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Storage Quota</h2>
            <p className="text-xs text-slate-400">Private object storage capacity allocation</p>
          </div>
        </div>

        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Used: {formatBytes(usedBytes)}</span>
            <span className="text-slate-400">Capacity: {formatBytes(maxStorageBytes)}</span>
          </div>

          <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
              style={{ width: `${storagePercent}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-500">
            {storagePercent}% of allocated private storage used across {stats?.total_documents || 0} documents.
          </p>
        </div>
      </div>

      {/* RAG Pipeline Specs Card */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6">
        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <div className="p-2.5 rounded-xl bg-slate-800 text-slate-300">
            <Cpu className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">RAG Engine Configuration</h2>
            <p className="text-xs text-slate-400">Backend indexing and retrieval hyperparameters</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-slate-500 block mb-1">Vector Index</span>
            <span className="text-slate-200 font-semibold">Postgres HNSW</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-slate-500 block mb-1">Embedding Dim</span>
            <span className="text-slate-200 font-semibold">1,536 dimensions</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-slate-500 block mb-1">Chunk Size</span>
            <span className="text-slate-200 font-semibold">800 chars / 150 overlap</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-slate-500 block mb-1">Retrieval Top-K</span>
            <span className="text-slate-200 font-semibold">5 passages</span>
          </div>
        </div>
      </div>

      {/* Security & Sign Out Card */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-slate-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">Session Security</h3>
            <p className="text-xs text-slate-400">End your active session on this device</p>
          </div>
        </div>

        <button
          onClick={logout}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:text-white bg-rose-500/10 hover:bg-rose-600 border border-rose-500/20 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  );
};
