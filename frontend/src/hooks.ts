import { useEffect, useRef, useState } from 'react';
import { ApiError, POLL_MS } from './api';

export interface Poll<T> { data?: T; error?: ApiError; loading: boolean; updated?: number }

export function usePoll<T>(fn: () => Promise<T>, ms = POLL_MS): Poll<T> {
  const [s, set] = useState<Poll<T>>({ loading: true });
  const ref = useRef(fn); ref.current = fn;
  useEffect(() => {
    let alive = true;
    const run = async () => {
      try { const d = await ref.current(); if (alive) set({ data: d, loading: false, updated: Date.now() }); }
      catch (e: any) { if (alive) set((p) => ({ ...p, error: e, loading: false })); }
    };
    run();
    const id = setInterval(run, ms);
    return () => { alive = false; clearInterval(id); };
  }, [ms]);
  return s;
}

export function useTheme() {
  const [theme, setTheme] = useState<string>(() => document.documentElement.dataset.theme || 'dark');
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('p2pcdn-theme', theme); } catch { /* storage unavailable */ }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))] as const;
}
