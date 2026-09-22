export function BrandMark({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 108 108" role="img" aria-label="SENTINEL">
      <defs>
        <linearGradient id="sentinel-shell" x1="18" y1="16" x2="92" y2="96" gradientUnits="userSpaceOnUse">
          <stop stopColor="#A9E4FF"/>
          <stop offset=".48" stopColor="#2DD4FF"/>
          <stop offset="1" stopColor="#0067D8"/>
        </linearGradient>
        <linearGradient id="sentinel-s" x1="26" y1="28" x2="82" y2="84" gradientUnits="userSpaceOnUse">
          <stop stopColor="#B9E9FF"/>
          <stop offset=".55" stopColor="#2DD4FF"/>
          <stop offset="1" stopColor="#00E0C2"/>
        </linearGradient>
        <filter id="sentinel-soft" x="-35%" y="-35%" width="170%" height="170%">
          <feGaussianBlur stdDeviation="1.3"/>
        </filter>
      </defs>
      <path d="M54 11C68 20 79 24 89 29L86 57C83 77 71 91 54 99C37 91 25 77 22 57L19 29C29 24 40 20 54 11Z" fill="url(#sentinel-shell)"/>
      <path d="M54 20C66 27 75 30 81 33L78 55C76 69 67 80 54 88C41 80 32 69 30 55L27 33C34 30 43 27 54 20Z" fill="#061018"/>
      <path d="M31 37C42 26 62 25 76 32C84 36 86 43 81 49C75 55 65 56 54 56C43 56 35 58 31 64C27 70 31 77 39 81C50 87 68 84 78 74" fill="none" stroke="url(#sentinel-s)" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M58 31C70 32 80 40 83 52M60 39C68 40 74 45 76 52" fill="none" stroke="#00E0C2" strokeOpacity=".68" strokeWidth="2.8" strokeLinecap="round"/>
      <circle cx="70" cy="52" r="5.6" fill="#00E0C2" opacity=".2" filter="url(#sentinel-soft)"/>
      <circle cx="70" cy="52" r="3.1" fill="#E9FFFF"/>
    </svg>
  );
}
