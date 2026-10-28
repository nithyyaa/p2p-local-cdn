import { ReactNode } from 'react';
const I = ({ children }: { children: ReactNode }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);
export const IconPulse = () => <I><path d="M3 12h4l3-8 4 16 3-8h4" /></I>;
export const IconPeers = () => <I><circle cx="9" cy="8" r="3" /><path d="M3 20v-1a5 5 0 0 1 5-5h2a5 5 0 0 1 5 5v1" /><path d="M17 4.5a3 3 0 0 1 0 6M21 20v-1a5 5 0 0 0-3-4.6" /></I>;
export const IconDisk = () => <I><ellipse cx="12" cy="6" rx="8" ry="3" /><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></I>;
export const IconSwap = () => <I><path d="M7 4 3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7" /></I>;
export const IconRadar = () => <I><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4" /><path d="M12 12 18 6" /></I>;
export const IconLog = () => <I><path d="M5 4h14v16H5zM9 9h6M9 13h6M9 17h3" /></I>;
export const Mark = () => (
  <svg viewBox="0 0 34 34" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="17" cy="17" r="4" fill="currentColor" /><circle cx="6" cy="9" r="2.5" /><circle cx="28" cy="9" r="2.5" /><circle cx="17" cy="29" r="2.5" /><path d="M8 10.5l6 4M26 10.5l-6 4M17 21v5.5" /></svg>
);
