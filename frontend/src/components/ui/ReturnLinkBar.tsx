import { Link } from "react-router-dom";
import type { ReturnLink } from "../../lib/internalNav";

export function ReturnLinkBar({ link }: { link: ReturnLink | null | undefined }) {
  if (!link) return null;
  return (
    <div className="border-b border-zinc-800/80 bg-zinc-900/40 px-4 py-2">
      <Link
        to={link.href}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-400 transition-colors hover:text-amber-300"
      >
        ← {link.label}
      </Link>
    </div>
  );
}
