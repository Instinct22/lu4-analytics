#!/usr/bin/env python3
"""Download all site images locally and rewrite remote URLs in datasets."""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "data" / "wiki" / "images"
I64_DIR = IMAGES_DIR / "i64"
RAID_DIR = IMAGES_DIR / "raid-bosses"
SKILLS_DIR = IMAGES_DIR / "wiki" / "skills"
CLASSES_DIR = IMAGES_DIR / "wiki" / "classes"

MASTERWORK = "https://masterwork.wiki"
L4MAP_I64 = "https://l4map.com/images/i64"

MIN_BYTES = 50
WORKERS = 16
TIMEOUT = 30.0
PNG_MAGIC = b"\x89PNG"


def local_raid_boss_image(npc_id: int, remote_url: str | None) -> str | None:
    """Prefer an existing local raid portrait; otherwise keep the remote URL."""
    if npc_id is None:
        return remote_url
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if is_valid(RAID_DIR / f"{npc_id}{ext}"):
            return f"images/raid-bosses/{npc_id}{ext}"
    return remote_url


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_valid(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= MIN_BYTES


def ext_from_url(url: str, default: str = ".png") -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    return suffix if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"} else default


def walk_class_ids(races: list[dict]) -> set[int]:
    ids: set[int] = set()

    def walk(node: dict) -> None:
        cid = node.get("id")
        if isinstance(cid, int):
            ids.add(cid)
        for child in node.get("children") or []:
            walk(child)

    for race in races:
        for branch in race.get("branches") or []:
            root = branch.get("root")
            if root:
                walk(root)
    return ids


def collect_tasks() -> list[tuple[str, Path, str]]:
    """Return (key, local_path, remote_url) for images that need downloading."""
    tasks: dict[str, tuple[Path, str]] = {}

    def add(key: str, local: Path, remote: str) -> None:
        if not remote or not remote.startswith("http"):
            return
        if key not in tasks:
            tasks[key] = (local, remote)

    # Raid bosses + drop icons
    raid_path = ROOT / "data" / "datasets" / "raid_bosses.json"
    if raid_path.exists():
        raid = load_json(raid_path)
        for boss in raid.get("bosses") or []:
            boss_id = boss.get("id")
            image = boss.get("image")
            if boss_id is not None and image and image.startswith("http"):
                ext = ext_from_url(image, ".jpg")
                local = RAID_DIR / f"{boss_id}{ext}"
                add(f"raid:{boss_id}", local, image)
            for group in boss.get("drops") or []:
                for item in group.get("items") or []:
                    icon = item.get("icon")
                    if icon and not icon.startswith("http"):
                        local = I64_DIR / icon
                        add(f"i64:{icon}", local, f"{L4MAP_I64}/{icon}")

    # Character skills / classes (fallback to masterwork if missing)
    char_path = ROOT / "data" / "datasets" / "character_data.json"
    if char_path.exists():
        char = load_json(char_path)
        for skill_id in char.get("skills") or {}:
            sid = int(skill_id)
            local = SKILLS_DIR / f"skill{sid}.png"
            if not is_valid(local):
                add(f"skill:{sid}", local, f"{MASTERWORK}/i64/skill{sid}.png")
        for cid in walk_class_ids(char.get("races") or []):
            icon_local = IMAGES_DIR / "wiki" / f"class_icon_{cid}.png"
            if not is_valid(icon_local):
                add(
                    f"class_icon:{cid}",
                    icon_local,
                    f"{MASTERWORK}/images/wiki/class_icon/class_icon_{cid}.png",
                )
            portrait_local = CLASSES_DIR / f"{cid}.png"
            if not is_valid(portrait_local):
                add(
                    f"class:{cid}",
                    portrait_local,
                    f"{MASTERWORK}/images/wiki/classes/{cid}.png",
                )

    # Item icons: prefer encyclopedia (full catalog), fall back to craft catalog.
    # Masterwork serves icons by filename under /i64/{icon}, not /images/{id}.png.
    item_icons: dict[int, str] = {}

    enc_path = ROOT / "data" / "datasets" / "items_encyclopedia.json"
    if enc_path.exists():
        enc = load_json(enc_path)
        for raw_id, meta in (enc.get("items") or {}).items():
            if not isinstance(meta, dict):
                continue
            icon = meta.get("icon")
            if not icon or not isinstance(icon, str):
                continue
            if icon.lower() in {"none.png", "none", "null", "undefined"}:
                continue
            try:
                iid = int(meta.get("id") if meta.get("id") is not None else raw_id)
            except (TypeError, ValueError):
                continue
            item_icons[iid] = icon

    craft_path = ROOT / "data" / "datasets" / "craft_catalog.json"
    if craft_path.exists():
        craft = load_json(craft_path)
        for raw_id, meta in (craft.get("items") or {}).items():
            try:
                iid = int(raw_id)
            except (TypeError, ValueError):
                continue
            if iid in item_icons:
                continue
            icon = meta.get("icon") if isinstance(meta, dict) else None
            if icon and isinstance(icon, str) and icon.lower() not in {
                "none.png",
                "none",
                "null",
                "undefined",
            }:
                item_icons[iid] = icon

    for iid, icon in item_icons.items():
        local = IMAGES_DIR / f"{iid}.png"
        if not is_valid(local):
            add(f"item:{iid}", local, f"{MASTERWORK}/i64/{icon}")

    # Dual weapon type icons
    for name in (
        "weapon_dual_sword_i00.png",
        "dual_dagger_i00.png",
        "weapon_r_dualblunt_i00.png",
    ):
        local = IMAGES_DIR / name
        if not is_valid(local):
            add(f"named:{name}", local, f"{L4MAP_I64}/{name}")

    return [(key, local, remote) for key, (local, remote) in sorted(tasks.items())]


def download_one(client: httpx.Client, key: str, local: Path, remote: str) -> tuple[str, str, str | None]:
    if is_valid(local):
        return key, "skipped", None
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = client.get(remote, follow_redirects=True)
        resp.raise_for_status()
        data = resp.content
        content_type = (resp.headers.get("content-type") or "").lower()
        if len(data) < MIN_BYTES:
            return key, "error", f"too small ({len(data)} bytes) from {remote}"
        if "image" not in content_type and not data.startswith(PNG_MAGIC):
            return key, "error", f"non-image content-type={content_type!r} from {remote}"
        tmp = local.with_suffix(local.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(local)
        return key, "downloaded", None
    except Exception as exc:
        if local.exists() and local.stat().st_size < MIN_BYTES:
            local.unlink(missing_ok=True)
        return key, "error", f"{remote}: {exc}"


def rewrite_raid_bosses() -> int:
    raid_path = ROOT / "data" / "datasets" / "raid_bosses.json"
    if not raid_path.exists():
        return 0
    raid = load_json(raid_path)
    updated = 0
    for boss in raid.get("bosses") or []:
        boss_id = boss.get("id")
        image = boss.get("image")
        if boss_id is None or not image or not image.startswith("http"):
            continue
        ext = ext_from_url(image, ".jpg")
        local = RAID_DIR / f"{boss_id}{ext}"
        if is_valid(local):
            new_path = f"images/raid-bosses/{boss_id}{ext}"
            if boss.get("image") != new_path:
                boss["image"] = new_path
                updated += 1
    if updated:
        save_json(raid_path, raid)
    return updated


def main() -> int:
    tasks = collect_tasks()
    pending = [(k, p, r) for k, p, r in tasks if not is_valid(p)]

    print(f"Image targets: {len(tasks)} total, {len(tasks) - len(pending)} already local, {len(pending)} to fetch")

    downloaded = skipped = errors = 0
    error_samples: list[str] = []

    with httpx.Client(
        timeout=TIMEOUT,
        headers={"User-Agent": "lu4-analytics/1.0 (+local image sync)"},
    ) as client:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {
                pool.submit(download_one, client, key, local, remote): key
                for key, local, remote in tasks
            }
            done = 0
            for fut in as_completed(futures):
                key, status, err = fut.result()
                done += 1
                if status == "downloaded":
                    downloaded += 1
                elif status == "skipped":
                    skipped += 1
                else:
                    errors += 1
                    if err and len(error_samples) < 20:
                        error_samples.append(f"{key}: {err}")
                if done % 50 == 0 or done == len(futures):
                    print(f"  progress {done}/{len(futures)}...", flush=True)

    rewritten = rewrite_raid_bosses()

    print()
    print("=== Result ===")
    print(f"Downloaded: {downloaded}")
    print(f"Already local (skipped): {skipped}")
    print(f"Errors: {errors}")
    print(f"Raid boss URLs rewritten to local paths: {rewritten}")
    if error_samples:
        print("\nSample errors:")
        for line in error_samples:
            print(f"  - {line}")

    return 1 if errors else 0


if __name__ == "__main__":
    t0 = time.perf_counter()
    code = main()
    print(f"\nElapsed: {time.perf_counter() - t0:.1f}s")
    sys.exit(code)
