import type { ReactNode } from "react";

interface Props {
  href: string;
  children: ReactNode;
  className?: string;
  stopPropagation?: boolean;
}

export default function WikiLink({
  href,
  children,
  className = "text-amber-400 underline-offset-2 hover:underline",
  stopPropagation = false,
}: Props) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      onClick={stopPropagation ? (e) => e.stopPropagation() : undefined}
    >
      {children}
    </a>
  );
}
