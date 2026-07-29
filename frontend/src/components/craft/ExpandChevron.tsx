/** SVG chevron — avoids Windows emoji rendering of ▶/▼ (blue background). */
export default function ExpandChevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 12 12"
      className="h-2.5 w-2.5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {open ? <path d="M3 4.5 6 7.5 9 4.5" /> : <path d="M4.5 3 7.5 6 4.5 9" />}
    </svg>
  );
}
