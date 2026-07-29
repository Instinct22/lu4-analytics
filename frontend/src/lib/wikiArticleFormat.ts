/**
 * Normalizes scraped wiki `content_md` into structured sections for readable UI.
 * Source pages are line-per-text-node dumps with nav chrome — not real markdown.
 */

export interface WikiFormatOptions {
  displayName?: string | null;
  entityType?: string | null;
}

export interface WikiPassport {
  subtitle?: string;
  grade?: string;
}

export type WikiArticleSection =
  | { type: "stats"; title: string; rows: Array<{ label: string; value: string }> }
  | { type: "restrictions"; title: string; items: string[] }
  | { type: "skills"; title: string; skills: Array<{ name: string; level?: string; description: string[] }> }
  | {
      type: "loot";
      title: string;
      kind: "drop" | "spoil";
      columns: string[];
      groups: Array<{ label?: string; rows: string[][] }>;
    }
  | {
      type: "enchant";
      title: string;
      columns: string[];
      rows: string[][];
    }
  | { type: "kv"; title: string; rows: Array<{ label: string; value: string }> }
  | { type: "prose"; title?: string; text: string };

export interface FormattedWikiArticle {
  passport: WikiPassport;
  sections: WikiArticleSection[];
}

const BRAND_LINES = new Set([
  "Lu4",
  "Eternal",
  "MasterWork",
  "Classes",
  "Skills",
  "Items",
  "NPC",
  "Quests",
  "Articles",
  "Search",
  "Ctrl+K",
  "English",
  "Русский",
  "Українська",
  "Start to Play",
  "Main",
]);

const BREADCRUMB_RE = /^(Items|NPCs|Sets|Skills|Classes|Quests)\s*\(Lu4\)$/i;

const STAT_LABELS = new Set([
  "HP / MP",
  "P. Atk. / M. Atk.",
  "P. Def. / M. Def.",
  "Accuracy / Evasion",
  "Exp / SP",
  "Attack Attribute",
  "Defense Attributes",
  "P. Def.",
  "M. Def.",
  "P. Atk.",
  "M. Atk.",
  "HP",
  "MP",
  "Weight",
  "NPC Sell Price",
  "Crystal Amount",
  "Soulshot / Spiritshot Consume",
  "P. Crit. Rate.",
  "P. Crit. Rate",
  "Critical",
  "Shield Defense",
  "Shield Defense Rate",
  "Speed",
  "Atk. Spd.",
  "Casting Spd.",
  "MP Consume",
  "Reuse Delay",
  "Range",
]);

const RESTRICTION_ITEMS = new Set([
  "Private Warehouse",
  "Clan Warehouse",
  "Transfer within Game Account",
  "Trade",
  "Drop",
  "Private Store",
  "Enchant",
  "Attribute",
  "Olympiad Use",
  "Freight",
]);

const SECTION_MARKERS = new Set([
  "Skills",
  "Drop",
  "Spoil",
  "Restrictions",
  "Enchant Bonuses",
  "Set Part",
  "Craft",
  "Locations",
]);

const GRADE_RE = /^(NG|D|C|B|A|S|S80|S84|R|R95|R99|R110)$/i;
const LEVEL_RE = /^Lv\.\s*\d+/i;
const CHANCE_RE = /^\d[\d\s]*([.,]\d+)?%$/;
const ENCHANT_LEVEL_RE = /^\+\d+$/;
const FOOTER_RE = /^(MasterWork\s+20\d{2}|All rights reserved)$/i;
const GROUP_CHANCE_RE = /^Group Chance:/i;

function extractContentBody(md: string): string {
  const idx = md.search(/^##\s+Content\s*$/m);
  if (idx >= 0) {
    const after = md.slice(idx).replace(/^##\s+Content\s*\n?/, "");
    const nextHeading = after.search(/^##\s+/m);
    return (nextHeading >= 0 ? after.slice(0, nextHeading) : after).trim();
  }
  return md
    .replace(/^#[^\n]*\n/, "")
    .replace(/^##\s+Stats[\s\S]*?(?=^##\s|\Z)/m, "")
    .trim();
}

function normalizeName(s: string): string {
  return s.replace(/\s+/g, " ").trim().toLowerCase();
}

function stripChrome(lines: string[], displayName?: string | null): string[] {
  const cleaned = lines.map((l) => l.trim()).filter((l) => l.length > 0);
  const end = cleaned.findIndex((l) => FOOTER_RE.test(l));
  const withoutFooter = end >= 0 ? cleaned.slice(0, end) : cleaned;

  const target = displayName ? normalizeName(displayName) : null;
  let start = 0;

  for (let i = 0; i < withoutFooter.length; i++) {
    if (BREADCRUMB_RE.test(withoutFooter[i])) {
      start = i + 1;
      break;
    }
  }

  // Body begins after the last title occurrence that still sits in the chrome zone
  // (breadcrumb → name → brand → name → actual content).
  if (target) {
    const nameHits: number[] = [];
    for (let i = start; i < Math.min(withoutFooter.length, start + 40); i++) {
      if (normalizeName(withoutFooter[i]) === target) nameHits.push(i);
    }
    if (nameHits.length >= 2) {
      start = nameHits[nameHits.length - 1] + 1;
    } else if (nameHits.length === 1) {
      start = nameHits[0] + 1;
    }
  }

  while (start < withoutFooter.length && BRAND_LINES.has(withoutFooter[start])) {
    start += 1;
  }

  if (target && start < withoutFooter.length && normalizeName(withoutFooter[start]) === target) {
    start += 1;
  }

  while (start < withoutFooter.length && BRAND_LINES.has(withoutFooter[start])) {
    start += 1;
  }

  return withoutFooter.slice(start);
}

function isSectionMarker(line: string): boolean {
  return SECTION_MARKERS.has(line);
}

function isStatLabel(line: string): boolean {
  return STAT_LABELS.has(line);
}

function looksLikePassportLine(line: string): boolean {
  if (GRADE_RE.test(line)) return true;
  if (/^(Weapon|Armor|Accessory|Other|Etc)\b/i.test(line)) return true;
  if (/,\s*Lv\.\s*\d+/i.test(line)) return true;
  if (/^(Humanoid|Animal|Monster|Plant|Undead|Demon|Spirit|Dragon|Giant|Bug|Fairy|Construct|Elemental|Divine|Siege Weapon)\b/i.test(line)) {
    return true;
  }
  return false;
}

function parsePassport(lines: string[]): { passport: WikiPassport; rest: string[] } {
  const passport: WikiPassport = {};
  let i = 0;

  if (i < lines.length && GRADE_RE.test(lines[i])) {
    passport.grade = lines[i];
    i += 1;
  }

  if (i < lines.length && looksLikePassportLine(lines[i]) && !isStatLabel(lines[i]) && !isSectionMarker(lines[i])) {
    passport.subtitle = lines[i];
    i += 1;
  } else if (!passport.grade && i < lines.length && looksLikePassportLine(lines[i])) {
    passport.subtitle = lines[i];
    i += 1;
  }

  return { passport, rest: lines.slice(i) };
}

function pushProse(sections: WikiArticleSection[], buf: string[], title?: string) {
  const text = buf.join("\n").trim();
  buf.length = 0;
  if (!text) return;
  sections.push({ type: "prose", title, text });
}

function parseRestrictions(lines: string[], start: number): { items: string[]; next: number } {
  const items: string[] = [];
  let i = start;
  while (i < lines.length) {
    const line = lines[i];
    if (isSectionMarker(line) && line !== "Drop") break;
    // "Drop" is both a restriction and a section — if next lines look like loot headers, stop.
    if (line === "Drop") {
      const nxt = lines[i + 1];
      if (nxt === "NPC" || nxt === "Item" || nxt === "Amount") break;
      items.push(line);
      i += 1;
      continue;
    }
    if (isStatLabel(line) || ENCHANT_LEVEL_RE.test(line)) break;
    if (RESTRICTION_ITEMS.has(line) || line.length < 40) {
      items.push(line);
      i += 1;
      continue;
    }
    break;
  }
  return { items, next: i };
}

function parseSkills(
  lines: string[],
  start: number,
): { skills: Array<{ name: string; level?: string; description: string[] }>; next: number } {
  const skills: Array<{ name: string; level?: string; description: string[] }> = [];
  let i = start;

  while (i < lines.length) {
    const line = lines[i];
    if (isSectionMarker(line) && line !== "Skills") break;
    if (isStatLabel(line)) break;

    const name = line;
    i += 1;
    let level: string | undefined;
    if (i < lines.length && LEVEL_RE.test(lines[i])) {
      level = lines[i];
      i += 1;
    }
    const description: string[] = [];
    while (i < lines.length) {
      const d = lines[i];
      if (isSectionMarker(d)) break;
      if (LEVEL_RE.test(d)) break;
      // Next skill: line followed by Lv. N
      if (i + 1 < lines.length && LEVEL_RE.test(lines[i + 1]) && !CHANCE_RE.test(d) && !isStatLabel(d)) {
        break;
      }
      if (isStatLabel(d)) break;
      description.push(d);
      i += 1;
    }
    if (name) skills.push({ name, level, description });
  }

  return { skills, next: i };
}

function isLootHeaderStart(lines: string[], i: number): boolean {
  const a = lines[i];
  const b = lines[i + 1];
  const c = lines[i + 2];
  if (a === "NPC" && b === "Amount" && c === "Chance") return true;
  if (a === "Item" && b === "Amount" && c === "Chance") return true;
  if (a === "Item" && b === "Grade" && c === "Amount") return true;
  return false;
}

function parseLoot(
  lines: string[],
  start: number,
  kind: "drop" | "spoil",
): {
  columns: string[];
  groups: Array<{ label?: string; rows: string[][] }>;
  next: number;
} {
  let i = start;
  const columns: string[] = [];

  // Consume header row: NPC|Item, Amount, Chance (and optional Grade)
  while (
    i < lines.length &&
    (lines[i] === "NPC" || lines[i] === "Item" || lines[i] === "Amount" || lines[i] === "Chance" || lines[i] === "Grade")
  ) {
    columns.push(lines[i]);
    i += 1;
  }
  if (columns.length === 0) {
    columns.push("Item", "Amount", "Chance");
  }

  const colCount = Math.max(columns.length, 3);
  const groups: Array<{ label?: string; rows: string[][] }> = [];
  let current: { label?: string; rows: string[][] } = { rows: [] };

  const flushGroup = () => {
    if (current.rows.length || current.label) groups.push(current);
    current = { rows: [] };
  };

  while (i < lines.length) {
    const line = lines[i];
    if (isSectionMarker(line) && line !== "Drop" && line !== "Spoil") break;
    if (line === "Drop" || line === "Spoil") break;
    if (isStatLabel(line)) break;
    // Second loot table (Drop → Spoil) repeats Item/Amount/Chance headers
    if (isLootHeaderStart(lines, i)) break;

    if (GROUP_CHANCE_RE.test(line)) {
      flushGroup();
      current = { label: line, rows: [] };
      i += 1;
      continue;
    }

    // Item drop rows often: Name, Grade?, Amount, Chance%
    // NPC drop rows (on item pages): Name, Lv. N, Amount, Chance%
    const row: string[] = [line];
    i += 1;
    while (i < lines.length && row.length < colCount + 1) {
      const n = lines[i];
      if (GROUP_CHANCE_RE.test(n)) break;
      if (isSectionMarker(n)) break;
      if (isStatLabel(n)) break;
      if (isLootHeaderStart(lines, i)) break;
      // New row starts when we already have a chance and next doesn't look like remaining cols
      if (row.length >= 3 && CHANCE_RE.test(row[row.length - 1])) break;
      if (
        row.length >= 2 &&
        CHANCE_RE.test(n) === false &&
        LEVEL_RE.test(n) === false &&
        GRADE_RE.test(n) === false &&
        !/^\d/.test(n) &&
        !/^\d[\d\s]*-\s*\d/.test(n) &&
        row.length >= colCount
      ) {
        break;
      }
      row.push(n);
      i += 1;
      if (CHANCE_RE.test(n) && row.length >= 3) break;
    }
    current.rows.push(row);
  }

  flushGroup();

  // Insert Level/Grade column when rows carry an extra field after the name.
  const maxLen = Math.max(0, ...groups.flatMap((g) => g.rows.map((r) => r.length)));
  if (maxLen === columns.length + 1 && columns[0] === "NPC") {
    columns.splice(1, 0, "Level");
  } else if (maxLen === columns.length + 1 && columns[0] === "Item") {
    columns.splice(1, 0, "Grade");
  }

  return { columns, groups, next: i };
}

function looksLikeLootSection(lines: string[], i: number): boolean {
  const nxt = lines[i + 1];
  if (nxt === "NPC" || nxt === "Item" || nxt === "Amount" || GROUP_CHANCE_RE.test(nxt ?? "")) return true;
  // Tab chrome: Drop / Spoil then table headers
  if ((lines[i] === "Drop" || lines[i] === "Spoil") && (nxt === "Drop" || nxt === "Spoil")) {
    return isLootHeaderStart(lines, i + 2) || isLootHeaderStart(lines, i + 1);
  }
  return false;
}

function skipLootTabChrome(lines: string[], i: number): number {
  // "Drop" "Spoil" before first table, or lone section title
  let j = i + 1;
  if (j < lines.length && (lines[j] === "Drop" || lines[j] === "Spoil")) j += 1;
  return j;
}

function parseEnchantBonuses(
  lines: string[],
  start: number,
): { columns: string[]; rows: string[][]; next: number } {
  let i = start;
  const columns: string[] = [];

  while (i < lines.length && !ENCHANT_LEVEL_RE.test(lines[i]) && !FOOTER_RE.test(lines[i])) {
    if (isSectionMarker(lines[i])) break;
    // Column headers until first +N
    if (
      /^(Enchant|Crystals|P\. Def|M\. Def|HP|P\. Atk|M\. Atk|Critical|Accuracy)/i.test(lines[i]) ||
      lines[i].includes("Crystallization") ||
      lines[i].includes("Failed Enchant") ||
      lines[i].includes("Bonus")
    ) {
      columns.push(lines[i]);
      i += 1;
      continue;
    }
    break;
  }

  const colCount = Math.max(columns.length, 2);
  const rows: string[][] = [];

  while (i < lines.length) {
    const line = lines[i];
    if (FOOTER_RE.test(line)) break;
    if (isSectionMarker(line)) break;
    if (!ENCHANT_LEVEL_RE.test(line) && rows.length > 0 && isStatLabel(line)) break;

    if (ENCHANT_LEVEL_RE.test(line)) {
      const row: string[] = [line];
      i += 1;
      // Take a fixed number of cells — HP Bonus values like "+12" must not start a new row.
      while (i < lines.length && row.length < colCount) {
        if (FOOTER_RE.test(lines[i])) break;
        if (isSectionMarker(lines[i])) break;
        row.push(lines[i]);
        i += 1;
      }
      rows.push(row);
      continue;
    }
    break;
  }

  return { columns: columns.length ? columns : ["Enchant", "Value"], rows, next: i };
}

/** Skip the compact crystallization preview that appears mid-item page before sell price. */
function skipCrystalPreview(lines: string[], start: number): number {
  let i = start;
  if (lines[i] !== "Crystallization" && lines[i] !== "Failed Enchant") return start;
  while (i < lines.length) {
    const line = lines[i];
    if (isStatLabel(line) || isSectionMarker(line)) return i;
    i += 1;
  }
  return i;
}

function parseBody(lines: string[]): WikiArticleSection[] {
  const sections: WikiArticleSection[] = [];
  const proseBuf: string[] = [];
  const statRows: Array<{ label: string; value: string }> = [];
  let i = 0;

  const flushStats = () => {
    if (!statRows.length) return;
    sections.push({
      type: "stats",
      title: "Характеристики",
      rows: [...statRows],
    });
    statRows.length = 0;
  };

  while (i < lines.length) {
    const line = lines[i];

    if (line === "Crystallization" || (line === "Failed Enchant" && lines[i + 1] && ENCHANT_LEVEL_RE.test(lines[i + 1]))) {
      pushProse(sections, proseBuf);
      flushStats();
      i = skipCrystalPreview(lines, i);
      continue;
    }

    if (line === "Restrictions") {
      pushProse(sections, proseBuf);
      flushStats();
      const { items, next } = parseRestrictions(lines, i + 1);
      if (items.length) {
        sections.push({ type: "restrictions", title: "Ограничения", items });
      }
      i = next;
      continue;
    }

    if (line === "Skills") {
      pushProse(sections, proseBuf);
      flushStats();
      const { skills, next } = parseSkills(lines, i + 1);
      if (skills.length) {
        sections.push({ type: "skills", title: "Навыки", skills });
      }
      i = next;
      continue;
    }

    if (line === "Drop" || line === "Spoil") {
      if (looksLikeLootSection(lines, i)) {
        pushProse(sections, proseBuf);
        flushStats();
        const kind: "drop" | "spoil" = line === "Spoil" && lines[i + 1] !== "Spoil" ? "spoil" : "drop";
        const headerAt = skipLootTabChrome(lines, i);
        const { columns, groups, next } = parseLoot(lines, headerAt, kind);
        if (groups.some((g) => g.rows.length)) {
          sections.push({
            type: "loot",
            title: kind === "spoil" ? "Спойл" : "Дроп",
            kind,
            columns,
            groups,
          });
        }
        i = next;
        // Repeated Item/Amount/Chance = Spoil table after Drop
        if (isLootHeaderStart(lines, i)) {
          const spoil = parseLoot(lines, i, "spoil");
          if (spoil.groups.some((g) => g.rows.length)) {
            sections.push({
              type: "loot",
              title: "Спойл",
              kind: "spoil",
              columns: spoil.columns,
              groups: spoil.groups,
            });
          }
          i = spoil.next;
        }
        continue;
      }
    }

    // Orphan second loot table without Drop/Spoil title
    if (isLootHeaderStart(lines, i)) {
      pushProse(sections, proseBuf);
      flushStats();
      const alreadyHasDrop = sections.some((s) => s.type === "loot" && s.kind === "drop");
      const kind: "drop" | "spoil" = alreadyHasDrop ? "spoil" : "drop";
      const { columns, groups, next } = parseLoot(lines, i, kind);
      if (groups.some((g) => g.rows.length)) {
        sections.push({
          type: "loot",
          title: kind === "spoil" ? "Спойл" : "Дроп",
          kind,
          columns,
          groups,
        });
      }
      i = next;
      continue;
    }

    if (line === "Enchant Bonuses") {
      pushProse(sections, proseBuf);
      flushStats();
      const { columns, rows, next } = parseEnchantBonuses(lines, i + 1);
      if (rows.length) {
        sections.push({ type: "enchant", title: "Бонусы заточки", columns, rows });
      }
      i = next;
      continue;
    }

    if (line === "Set Part") {
      pushProse(sections, proseBuf);
      flushStats();
      const values: string[] = [];
      i += 1;
      while (i < lines.length && !isSectionMarker(lines[i]) && !isStatLabel(lines[i])) {
        if (GRADE_RE.test(lines[i]) && values.length) {
          values[values.length - 1] = `${values[values.length - 1]} ${lines[i]}`;
          i += 1;
          break;
        }
        values.push(lines[i]);
        i += 1;
        if (values.length >= 2) break;
      }
      sections.push({
        type: "kv",
        title: "Сет",
        rows: [{ label: "Часть сета", value: values.join(" ").trim() }],
      });
      continue;
    }

    if (isStatLabel(line) && i + 1 < lines.length) {
      pushProse(sections, proseBuf);
      const value = lines[i + 1];
      // Don't treat section-like values as stats
      if (!isSectionMarker(value) || value === "Drop") {
        statRows.push({ label: line, value });
        i += 2;
        continue;
      }
    }

    proseBuf.push(line);
    i += 1;
  }

  pushProse(sections, proseBuf);
  flushStats();

  // Merge consecutive stats that got split (flushStats before sections) — already one block usually.
  return coalesceStats(sections);
}

function coalesceStats(sections: WikiArticleSection[]): WikiArticleSection[] {
  const out: WikiArticleSection[] = [];
  for (const s of sections) {
    const prev = out[out.length - 1];
    if (s.type === "stats" && prev?.type === "stats") {
      prev.rows.push(...s.rows);
    } else {
      out.push(s);
    }
  }
  return out;
}

export function formatWikiArticle(
  contentMd: string | null | undefined,
  options: WikiFormatOptions = {},
): FormattedWikiArticle {
  if (!contentMd?.trim()) {
    return { passport: {}, sections: [{ type: "prose", text: "Нет контента" }] };
  }

  const body = extractContentBody(contentMd);
  const rawLines = body.split(/\r?\n/);
  const stripped = stripChrome(rawLines, options.displayName);
  const { passport, rest } = parsePassport(stripped);
  const sections = parseBody(rest);

  if (!sections.length) {
    return {
      passport,
      sections: [{ type: "prose", text: stripped.join("\n") || "Нет контента" }],
    };
  }

  return { passport, sections };
}
