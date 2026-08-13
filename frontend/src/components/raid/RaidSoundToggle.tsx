type Props = {
  enabled: boolean;
  onToggle: () => void;
};

export default function RaidSoundToggle({ enabled, onToggle }: Props) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={enabled}
      title={
        enabled
          ? "Звук включён: «Скоро» и «Окно респа». Нажмите, чтобы выключить."
          : "Звук выключен. При переходе в «Скоро» (30 мин) и «Окно респа» будет музыка."
      }
      className={[
        "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
        enabled
          ? "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:border-amber-400/60 hover:bg-amber-500/15"
          : "border-zinc-700/80 bg-zinc-900/60 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200",
      ].join(" ")}
    >
      <span aria-hidden>{enabled ? "🔊" : "🔇"}</span>
      <span>{enabled ? "Звук: вкл" : "Звук: выкл"}</span>
    </button>
  );
}
