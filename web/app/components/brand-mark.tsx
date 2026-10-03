export function BrandMark({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" role="img" aria-label="SENTINEL" fill="none">
      <path d="M32 5 55 16v16c0 13-9 22-23 27C18 54 9 45 9 32V16L32 5Z" stroke="currentColor" strokeWidth="4" strokeLinejoin="round" />
      <path d="M43 19H27l-7 8 23 10-7 8H21" stroke="currentColor" strokeWidth="6" strokeLinecap="square" strokeLinejoin="bevel" />
    </svg>
  );
}
