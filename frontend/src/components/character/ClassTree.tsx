import type { ClassTreeNode } from "../../lib/characterData";
import { wikiClassUrl } from "../../lib/characterData";
import ClassIcon from "./ClassIcon";
import WikiLink from "./WikiLink";

interface Props {
  node: ClassTreeNode;
  selectedId: number | null;
  onSelect: (classId: number) => void;
  wikiBase: string;
  depth?: number;
}

function TreeNode({ node, selectedId, onSelect, wikiBase, depth = 0 }: Props) {
  const selected = selectedId === node.id;
  const hasChildren = node.children.length > 0;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => onSelect(node.id)}
        className={[
          "group flex w-full items-center gap-2 rounded-xl px-2 py-2 text-left transition-all",
          selected
            ? "bg-amber-500/15 ring-1 ring-amber-500/40"
            : "hover:bg-zinc-800/70",
        ].join(" ")}
        style={{ paddingLeft: `${8 + depth * 12}px` }}
      >
        <ClassIcon id={node.id} size={depth === 0 ? 44 : 36} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className={["truncate text-sm font-medium", selected ? "text-amber-300" : "text-zinc-200"].join(" ")}>
              {node.name}
            </span>
            <WikiLink
              href={wikiClassUrl(node.slug, undefined, wikiBase)}
              stopPropagation
              className="shrink-0 text-[0.65rem] text-zinc-600 hover:text-amber-400"
              aria-label={`${node.name} на Wiki`}
            >
              ↗
            </WikiLink>
          </div>
          {depth === 0 && (
            <div className="text-[0.65rem] uppercase tracking-wide text-zinc-500">Базовый класс</div>
          )}
        </div>
      </button>

      {hasChildren && (
        <div className="relative ml-5 border-l border-zinc-700/80 pl-2">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              selectedId={selectedId}
              onSelect={onSelect}
              wikiBase={wikiBase}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface TreeProps {
  branches: Array<{ type: string; root: ClassTreeNode }>;
  selectedId: number | null;
  onSelect: (classId: number) => void;
  wikiBase: string;
}

export default function ClassTree({ branches, selectedId, onSelect, wikiBase }: TreeProps) {
  return (
    <div className="space-y-4">
      {branches.map((branch) => (
        <div key={`${branch.type}-${branch.root.id}`}>
          <div className="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-zinc-500">
            {branch.type === "mage" ? "Магическая ветка" : "Боевая ветка"}
          </div>
          <TreeNode node={branch.root} selectedId={selectedId} onSelect={onSelect} wikiBase={wikiBase} />
        </div>
      ))}
    </div>
  );
}
