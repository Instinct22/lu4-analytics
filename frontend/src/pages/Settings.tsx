import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  updateAdminLevelPreset,
  updateAdminLevelRestriction,
} from "../api/admin";
import LevelRangeControl from "../components/settings/LevelRangeControl";
import { PageHeader } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useLevelRange, useLevelSettingsQuery } from "../hooks/useLevelRange";
import { DEFAULT_LEVEL_RANGE, LEVEL_ABSOLUTE_MAX, LEVEL_ABSOLUTE_MIN, type LevelRange } from "../lib/levelRange";

function LevelSettingsSection({
  title,
  description,
  value,
  onSave,
  sliderMin,
  sliderMax,
  readOnly,
  saving,
  saved,
  error,
}: {
  title: string;
  description: string;
  value: LevelRange;
  onSave: (next: LevelRange) => void;
  sliderMin: number;
  sliderMax: number;
  readOnly: boolean;
  saving: boolean;
  saved: boolean;
  error: boolean;
}) {
  const [draft, setDraft] = useState(value);
  const dirty = draft.min !== value.min || draft.max !== value.max;

  useEffect(() => {
    setDraft(value);
  }, [value.min, value.max]);

  return (
    <section className="card space-y-4 !p-5">
      <div>
        <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
        <p className="mt-1 text-sm text-zinc-500">{description}</p>
      </div>
      {readOnly ? (
        <p className="text-sm tabular-nums text-zinc-300">
          {value.min} – {value.max} lvl
        </p>
      ) : (
        <>
          <LevelRangeControl
            value={draft}
            onChange={setDraft}
            sliderMin={sliderMin}
            sliderMax={sliderMax}
          />
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn-primary"
              disabled={!dirty || saving}
              onClick={() => onSave(draft)}
            >
              {saving ? "Сохранение…" : "Сохранить"}
            </button>
            {saved && <span className="text-sm text-emerald-400">Сохранено</span>}
            {error && <span className="text-sm text-red-400">Не удалось сохранить</span>}
          </div>
        </>
      )}
    </section>
  );
}

export default function SettingsPage() {
  const { hasPermission, isSuperadmin } = useAuth();
  const { unrestricted, restriction } = useLevelRange();
  const { presetQuery, restrictionQuery } = useLevelSettingsQuery();
  const queryClient = useQueryClient();

  const canEditPreset = hasPermission("admin.level_preset");
  const preset = presetQuery.data ?? DEFAULT_LEVEL_RANGE;
  const restrictionValue = restrictionQuery.data ?? restriction ?? DEFAULT_LEVEL_RANGE;

  const [presetSaved, setPresetSaved] = useState(false);
  const [restrictionSaved, setRestrictionSaved] = useState(false);

  const presetMutation = useMutation({
    mutationFn: updateAdminLevelPreset,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["level-preset"] });
      setPresetSaved(true);
      window.setTimeout(() => setPresetSaved(false), 2500);
    },
  });

  const restrictionMutation = useMutation({
    mutationFn: updateAdminLevelRestriction,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["level-restriction"] });
      setRestrictionSaved(true);
      window.setTimeout(() => setRestrictionSaved(false), 2500);
    },
  });

  return (
    <div className="min-h-full">
      <PageHeader title="Настройки">
        <p className="text-sm text-zinc-500">Общие преднастройки фильтров для всех пользователей</p>
      </PageHeader>

      <div className="max-w-xl space-y-5">
        <LevelSettingsSection
          title="Предустановка уровня"
          description="Общий диапазон по умолчанию для всех пользователей. Не зависит от ограничения — это только удобная стартовая точка."
          value={preset}
          onSave={(next) => presetMutation.mutate(next)}
          sliderMin={LEVEL_ABSOLUTE_MIN}
          sliderMax={LEVEL_ABSOLUTE_MAX}
          readOnly={!canEditPreset}
          saving={presetMutation.isPending}
          saved={presetSaved}
          error={presetMutation.isError}
        />
        <p className="-mt-3 px-1 text-sm text-zinc-500">
          Применяется в{" "}
          <Link to="/resources" className="text-amber-400/90 hover:text-amber-300">
            ресурсах
          </Link>{" "}
          и{" "}
          <Link to="/raid-bosses" className="text-amber-400/90 hover:text-amber-300">
            рейд-боссах
          </Link>
          . Изменение доступно с правом «Предустановка уровня».
        </p>

        {!unrestricted && restriction && (
          <p className="text-sm text-amber-400/90">
            Для пользователей без права «Уровни без ограничений» доступен диапазон{" "}
            {restriction.min}–{restriction.max} lvl.
          </p>
        )}

        {isSuperadmin && (
          <LevelSettingsSection
            title="Ограничение уровня"
            description="Глобальные границы для пользователей без права «Уровни без ограничений». Доступно только суперадмину."
            value={restrictionValue}
            onSave={(next) => restrictionMutation.mutate(next)}
            sliderMin={1}
            sliderMax={99}
            readOnly={false}
            saving={restrictionMutation.isPending}
            saved={restrictionSaved}
            error={restrictionMutation.isError}
          />
        )}
      </div>
    </div>
  );
}
