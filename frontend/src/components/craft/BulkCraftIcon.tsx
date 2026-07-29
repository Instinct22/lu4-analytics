/** Mass-craft queue: hammer + anvil (not a shopping cart). */
export default function BulkCraftIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M4 18h16" />
      <path d="M6 18 7.5 15h9L18 18" />
      <path d="M8.5 15V12a3.5 3.5 0 0 1 7 0v3" />
      <path
        d="M15.5 6.5 18.5 9.5 14 14 11 11 15.5 6.5z"
        fill="currentColor"
        stroke="none"
      />
      <path d="M11.5 11 8 14.5" />
    </svg>
  );
}
