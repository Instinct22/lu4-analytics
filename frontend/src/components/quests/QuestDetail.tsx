import { ItemIcon } from "../craft/CraftCostBar";
import type { QuestDetail } from "../../api/quests";
import { formatQuestLevel, i64IconUrl, questStepImageUrl } from "../../lib/quests";
import { itemPagePath } from "../../lib/internalNav";
import { Link } from "react-router-dom";

function WikiIcon({
  icon,
  itemId,
  size = 32,
  alt = "",
}: {
  icon?: string | null;
  itemId?: number | null;
  size?: number;
  alt?: string;
}) {
  const remote = i64IconUrl(icon);
  if (remote) {
    return (
      <div
        className="flex shrink-0 items-center justify-center overflow-hidden rounded-lg bg-zinc-800 ring-1 ring-zinc-700/80"
        style={{ width: size, height: size }}
      >
        <img
          src={remote}
          alt={alt}
          width={size}
          height={size}
          className="h-full w-full object-contain"
          loading="lazy"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>
    );
  }
  if (itemId != null) {
    return <ItemIcon id={itemId} size={size} />;
  }
  return (
    <div
      className="shrink-0 rounded-lg bg-zinc-800 ring-1 ring-zinc-700/80"
      style={{ width: size, height: size }}
    />
  );
}

type Props = {
  quest: QuestDetail;
  onClose?: () => void;
};

export default function QuestDetail({ quest, onClose }: Props) {
  const level = formatQuestLevel(quest.level_min, quest.level_max);

  return (
    <div className="card space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">{quest.name}</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Уровень {level}
            {quest.start_npc?.name ? ` · NPC: ${quest.start_npc.name}` : ""}
          </p>
        </div>
        {onClose && (
          <button type="button" className="btn-ghost text-sm" onClick={onClose}>
            Закрыть
          </button>
        )}
      </div>

      {quest.description && (
        <p className="text-sm leading-relaxed text-zinc-300">{quest.description}</p>
      )}

      {quest.start_npc && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Start NPC
          </h3>
          <div className="flex items-center gap-3 rounded-xl bg-zinc-950/50 px-3 py-2 ring-1 ring-zinc-800/80">
            <WikiIcon icon={quest.start_npc.icon} size={40} alt={quest.start_npc.name} />
            <div>
              <p className="text-sm font-medium text-zinc-100">{quest.start_npc.name}</p>
              {quest.start_npc.id != null && (
                <p className="text-xs text-zinc-500">ID {quest.start_npc.id}</p>
              )}
            </div>
          </div>
        </section>
      )}

      {quest.rewards.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Награды
          </h3>
          <ul className="space-y-2">
            {quest.rewards.map((reward, idx) => {
              const content = (
                <div className="flex items-center gap-3 rounded-xl bg-zinc-950/50 px-3 py-2 ring-1 ring-zinc-800/80">
                  <WikiIcon
                    icon={reward.icon}
                    itemId={reward.item_id}
                    size={36}
                    alt={reward.name}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-100">{reward.name}</p>
                    <p className="text-xs text-zinc-500">
                      {[reward.grade, reward.qty != null ? `×${reward.qty.toLocaleString("ru-RU")}` : null]
                        .filter(Boolean)
                        .join(" · ") || "—"}
                    </p>
                  </div>
                </div>
              );
              return (
                <li key={`${reward.item_id ?? reward.name}-${idx}`}>
                  {reward.item_id != null ? (
                    <Link to={itemPagePath(reward.item_id)} className="block hover:opacity-90">
                      {content}
                    </Link>
                  ) : (
                    content
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {quest.steps.length > 0 && (
        <section>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Прохождение
          </h3>
          <ol className="space-y-4">
            {quest.steps.map((step, idx) => (
              <li key={`${step.title}-${idx}`} className="space-y-2">
                <h4 className="text-sm font-semibold text-zinc-200">
                  {step.title || `Шаг ${idx + 1}`}
                </h4>
                {step.images.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {step.images.map((src) => {
                      const url = questStepImageUrl(src);
                      if (!url) return null;
                      return (
                        <a
                          key={src}
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="block overflow-hidden rounded-xl ring-1 ring-zinc-800"
                        >
                          <img
                            src={url}
                            alt=""
                            className="max-h-48 max-w-full object-contain"
                            loading="lazy"
                            referrerPolicy="no-referrer"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = "none";
                            }}
                          />
                        </a>
                      );
                    })}
                  </div>
                )}
                {step.text && (
                  <p className="whitespace-pre-line text-sm leading-relaxed text-zinc-400">
                    {step.text}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
