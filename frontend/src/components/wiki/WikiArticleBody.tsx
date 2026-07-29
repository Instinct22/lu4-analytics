import {
  formatWikiArticle,
  type FormattedWikiArticle,
  type WikiArticleSection,
} from "../../lib/wikiArticleFormat";

interface Props {
  contentMd: string | null | undefined;
  displayName?: string | null;
  entityType?: string | null;
}

function SectionTitle({ children }: { children: string }) {
  return <h3 className="wiki-article__section-title">{children}</h3>;
}

function Passport({ passport }: { passport: FormattedWikiArticle["passport"] }) {
  if (!passport.grade && !passport.subtitle) return null;
  return (
    <div className="wiki-article__passport">
      {passport.grade && <span className="wiki-article__grade">{passport.grade}</span>}
      {passport.subtitle && <p className="wiki-article__subtitle">{passport.subtitle}</p>}
    </div>
  );
}

function StatsSection({ section }: { section: Extract<WikiArticleSection, { type: "stats" }> }) {
  return (
    <section className="wiki-article__section">
      <SectionTitle>{section.title}</SectionTitle>
      <dl className="wiki-article__stats">
        {section.rows.map((row) => (
          <div key={`${row.label}-${row.value}`} className="wiki-article__stat">
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function RestrictionsSection({
  section,
}: {
  section: Extract<WikiArticleSection, { type: "restrictions" }>;
}) {
  return (
    <section className="wiki-article__section">
      <SectionTitle>{section.title}</SectionTitle>
      <div className="wiki-article__chips">
        {section.items.map((item) => (
          <span key={item} className="wiki-article__chip">
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}

function SkillsSection({ section }: { section: Extract<WikiArticleSection, { type: "skills" }> }) {
  return (
    <section className="wiki-article__section">
      <SectionTitle>{section.title}</SectionTitle>
      <ul className="wiki-article__skills">
        {section.skills.map((skill) => (
          <li key={`${skill.name}-${skill.level ?? ""}`} className="wiki-article__skill">
            <div className="wiki-article__skill-head">
              <span className="wiki-article__skill-name">{skill.name}</span>
              {skill.level && <span className="wiki-article__skill-lv">{skill.level}</span>}
            </div>
            {skill.description.length > 0 && (
              <p className="wiki-article__skill-desc">{skill.description.join("\n")}</p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function LootSection({ section }: { section: Extract<WikiArticleSection, { type: "loot" }> }) {
  return (
    <section className="wiki-article__section">
      <SectionTitle>{section.title}</SectionTitle>
      {section.groups.map((group, gi) => (
        <div key={gi} className="wiki-article__loot-group">
          {group.label && <p className="wiki-article__loot-label">{group.label}</p>}
          <div className="wiki-article__table-wrap">
            <table className="wiki-article__table">
              <thead>
                <tr>
                  {section.columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {group.rows.map((row, ri) => (
                  <tr key={ri}>
                    {section.columns.map((_, ci) => (
                      <td key={ci}>{row[ci] ?? "—"}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </section>
  );
}

function EnchantSection({ section }: { section: Extract<WikiArticleSection, { type: "enchant" }> }) {
  return (
    <section className="wiki-article__section">
      <SectionTitle>{section.title}</SectionTitle>
      <div className="wiki-article__table-wrap">
        <table className="wiki-article__table">
          <thead>
            <tr>
              {section.columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {section.rows.map((row, ri) => (
              <tr key={ri}>
                {section.columns.map((_, ci) => (
                  <td key={ci}>{row[ci] ?? "—"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function KvSection({ section }: { section: Extract<WikiArticleSection, { type: "kv" }> }) {
  return (
    <section className="wiki-article__section">
      <SectionTitle>{section.title}</SectionTitle>
      <dl className="wiki-article__stats">
        {section.rows.map((row) => (
          <div key={row.label} className="wiki-article__stat">
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ProseSection({ section }: { section: Extract<WikiArticleSection, { type: "prose" }> }) {
  return (
    <section className="wiki-article__section">
      {section.title && <SectionTitle>{section.title}</SectionTitle>}
      <p className="wiki-article__prose">{section.text}</p>
    </section>
  );
}

function renderSection(section: WikiArticleSection, index: number) {
  switch (section.type) {
    case "stats":
      return <StatsSection key={index} section={section} />;
    case "restrictions":
      return <RestrictionsSection key={index} section={section} />;
    case "skills":
      return <SkillsSection key={index} section={section} />;
    case "loot":
      return <LootSection key={index} section={section} />;
    case "enchant":
      return <EnchantSection key={index} section={section} />;
    case "kv":
      return <KvSection key={index} section={section} />;
    case "prose":
      return <ProseSection key={index} section={section} />;
    default:
      return null;
  }
}

export default function WikiArticleBody({ contentMd, displayName, entityType }: Props) {
  const formatted = formatWikiArticle(contentMd, { displayName, entityType });

  return (
    <div className="wiki-article">
      <Passport passport={formatted.passport} />
      <div className="wiki-article__body">{formatted.sections.map(renderSection)}</div>
    </div>
  );
}
