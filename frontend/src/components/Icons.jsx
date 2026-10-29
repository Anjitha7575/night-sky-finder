export const Planet = () => (
  <svg viewBox="0 0 64 64" aria-hidden="true">
    <defs>
      <radialGradient id="pl" cx="35%" cy="30%">
        <stop offset="0" stopColor="#bfe0ff" />
        <stop offset="1" stopColor="#2f7fe0" />
      </radialGradient>
    </defs>
    <ellipse cx="32" cy="34" rx="29" ry="9" fill="none" stroke="#9fcbff" strokeWidth="3" transform="rotate(-18 32 34)" opacity="0.6" />
    <circle cx="32" cy="32" r="17" fill="url(#pl)" />
    <path d="M5 43 A29 9 -18 0 0 59 25" fill="none" stroke="#d8ebff" strokeWidth="3" transform="rotate(0)" />
  </svg>
);

export const Library = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
    <ellipse cx="12" cy="5" rx="8" ry="3" />
    <path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
    <path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
  </svg>
);

export const Play = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="11" fill="currentColor" />
    <path d="M10 8l6 4-6 4z" fill="#0b1426" />
  </svg>
);

export const Streak = () => (
  <svg viewBox="0 0 40 40" aria-hidden="true" fill="none" stroke="currentColor" strokeLinecap="round">
    <path d="M34 6 L12 28" strokeWidth="3" />
    <circle cx="10" cy="30" r="4" fill="currentColor" stroke="none" />
  </svg>
);

export const Camera = () => (
  <svg viewBox="0 0 48 48" aria-hidden="true">
    <rect x="4" y="12" width="28" height="24" rx="5" fill="#5aa2ff" />
    <path d="M32 21l11-6v18l-11-6z" fill="#5aa2ff" />
    <circle cx="13" cy="9" r="4" fill="#5aa2ff" />
    <circle cx="24" cy="9" r="4" fill="#5aa2ff" />
  </svg>
);

export const Gear = () => (
  <svg viewBox="0 0 48 48" aria-hidden="true">
    <g fill="#3d8bff">
      {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
        <rect key={a} x="20" y="3" width="8" height="10" rx="2" transform={`rotate(${a} 24 24)`} />
      ))}
      <circle cx="24" cy="24" r="15" />
    </g>
    <circle cx="24" cy="24" r="6" fill="#0b1426" />
  </svg>
);

export const Brain = () => (
  <svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="#9b7bff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M24 8v32" />
    <path d="M24 10c-2-3-8-3-9 1-4-1-7 3-5 6-3 2-3 7 0 9-2 3 0 7 4 7 1 4 7 5 10 1" />
    <path d="M24 10c2-3 8-3 9 1 4-1 7 3 5 6 3 2 3 7 0 9 2 3 0 7-4 7-1 4-7 5-10 1" />
    <path d="M15 18c2 0 4 1 5 3M14 28c2-1 5-1 6 1M33 18c-2 0-4 1-5 3M34 28c-2-1-5-1-6 1" />
  </svg>
);

export const Info = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 11v6M12 7.5v.5" strokeLinecap="round" />
  </svg>
);

export const Upload = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 16V4M7 9l5-5 5 5" />
    <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
  </svg>
);

export const Copy = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8">
    <rect x="8" y="8" width="12" height="12" rx="2" />
    <path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3" />
  </svg>
);
