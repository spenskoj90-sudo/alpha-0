export function BrandMark({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" role="img" aria-label="SENTINEL" fill="none">
      <path d="M32 4 56 15.5v17.2c0 13.7-9 23-24 28.7C17 55.7 8 46.4 8 32.7V15.5L32 4Z" stroke="currentColor" strokeWidth="4" strokeLinejoin="round" />
      <path d="M43 18.5c-3.2-2.2-7.1-3.4-11.2-3.4-7.1 0-11.8 3.2-11.8 7.9 0 4.3 3.5 6.8 10.1 8.5l4.2 1.1c6.5 1.7 9.7 4.2 9.7 8.4 0 5.1-4.8 8.8-12 8.8-4.9 0-9.1-1.5-12.5-4.4" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
      <circle cx="46.5" cy="29.5" r="2.5" fill="currentColor" />
    </svg>
  );
}
