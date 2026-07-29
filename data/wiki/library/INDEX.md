# Knowledge Library — masterwork.wiki (`/lu4/`)

Local, AI-queryable mirror of the `/lu4/` section of masterwork.wiki.
Built by `crawl.py` (fetch) + `build_library.py` (structure). This file is the
entry point: read it first, then query the layers below in order (cheapest first).

## How this library is produced

1. `python crawl.py` — walks `/lu4/` breadth-first, saves raw HTML into
   `raw/`, tracks progress in `../roadmap.json` (resumable, skips visited pages).
2. `python build_library.py` — turns `raw/` into `data/`, `pages/`, `index/`.
   Local only, incremental (`--force` rebuilds all).

`raw/` is the source of truth; every other layer can be regenerated from it.

## Layers (query in this order)

| Layer | Path | Use for | Cost |
|-------|------|---------|------|
| Index | `index/catalog.jsonl` | find an entity by name/type | cheap (1 line/entity) |
| Data | `data/<type>/<id>-<slug>.json` | all facts + relations of one entity | 1 Read |
| Pages | `pages/<type>/<id>-<slug>.md` | prose / full-text search | grep |
| Graph | `index/graph.json` | multi-hop links (materials, references) | 1 Read |
| Raw | `raw/…​.html` | re-extraction, last resort | expensive |

## Recommended query flow (for the AI answering a question)

1. **Locate**: `grep` the entity name in `index/catalog.jsonl`
   (or look it up in `index/by_name.json`). Each row gives `type`, `id`, `url`,
   and the path to its `data` and `page` files.
2. **Read facts**: open the entity's `data/*.json` — it has `stats`,
   `materials`, and internal `links` already parsed. Usually enough.
3. **Multi-hop**: for questions like "full craft tree" or "everything that
   references X", walk `index/graph.json` (`needs` = recipe materials,
   `references` = all internal links on the page).
4. **Prose / details**: `grep` or read `pages/*.md` for free text.
5. **Fallback**: only if something wasn't extracted, read the `raw/*.html`.

## File schemas

### `index/catalog.jsonl` — one JSON object per line
```json
{"key":"item:157","id":157,"type":"item","name":"Spiked Club",
 "url":"/lu4/item/157-spiked-club","source_url":"https://masterwork.wiki/lu4/item/157-spiked-club",
 "data":"library/data/item/157-spiked-club.json",
 "page":"library/pages/item/157-spiked-club.md","summary":"item, Grade NG, 3 materials"}
```

### `data/<stem>.json` — one entity
```json
{"key":"item:157","type":"item","id":157,"name":"Spiked Club",
 "url":"/lu4/item/157-spiked-club","source_url":"https://masterwork.wiki/lu4/item/157-spiked-club",
 "raw_html":"library/raw/lu4/item/157-spiked-club.html",
 "stats":{"Grade":"NG","Type":"Weapon"},
 "materials":[{"key":"item:1867","type":"item","id":1867,"name":"Animal Skin","amount":"10"}],
 "links":[{"key":"npc:20011","type":"npc","id":20011,"name":"...","url":"/lu4/npc/20011-..."}]}
```

### `index/by_name.json` — name lookup
Lowercased name → list of keys, e.g. `{"spiked club": ["item:157"]}`.

### `index/graph.json` — relationships
```json
{"item:157": {"type":"item","name":"Spiked Club",
  "needs":["item:1867"], "references":["npc:20011","item:1867"]}}
```
- `needs`: recipe materials (dependency edges).
- `references`: every internal `/lu4/` entity linked from the page.

Entity `key` format is `<type>:<id>` (e.g. `item:157`, `npc:20011`,
`location:12`). Non-entity pages use `page:<sanitized_url>`.

## Notes

- Every raw file starts with a `<!-- saved-from: <url> ... -->` banner, and the
  original page link is carried into `source_url` in the catalog and each
  `data/*.json` (and the `Source:` line in `pages/*.md`). If archived info looks
  incomplete, open that link to re-check the live page.
- Names/items are English by default; some localized fields (e.g. locations)
  may appear in Russian — acceptable.
- `../roadmap.json` reflects crawl progress: `visited`, `frontier` (queue),
  `failed`. A non-empty `frontier` means the crawl is incomplete — re-run
  `crawl.py` to continue.
- After any re-crawl, re-run `build_library.py` to refresh the derived layers.
