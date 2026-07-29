"""Tests for item encyclopedia parser and classifier."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from craft_catalog.item_classify import classify_section, is_excluded, sealed_base_name  # noqa: E402
from craft_catalog.wiki_parse import load_html, parse_item_full  # noqa: E402

ITEM_RAW = ROOT / "data" / "wiki" / "library" / "raw" / "lu4" / "item"


@pytest.mark.skipif(not ITEM_RAW.is_dir(), reason="wiki raw items missing")
def test_orfen_earring_drop_and_enchant():
    item = parse_item_full(ITEM_RAW, 6661, "/lu4/item/6661-earring-of-orfen")
    assert item["name"] == "Earring of Orfen"
    assert item["grade"] == "C"
    assert len(item.get("drops") or []) >= 1
    assert item["drops"][0]["npc_name"] == "Orfen"
    assert len(item.get("enchant") or []) >= 8
    assert item.get("restrictions", {}).get("trade") is True
    assert item.get("stats", {}).get("m_def") == 63


@pytest.mark.skipif(not ITEM_RAW.is_dir(), reason="wiki raw items missing")
def test_scroll_drop_spoil_pagination_merge():
    item = parse_item_full(ITEM_RAW, 960, "/lu4/item/960-scroll-enchant-armor-s-grade")
    assert len(item.get("drops") or []) > 15
    assert len(item.get("spoils") or []) > 0


def test_classify_excludes_quest_and_shadow():
    assert is_excluded("Foo", "C", "Quest Item / Foo")
    assert is_excluded("Shadow Sword", "C", "Weapon / Sword")
    assert is_excluded("Adena", "Common", "Money")
    assert not is_excluded("Sword", "C", "Weapon / Sword")


def test_classify_sections():
    assert classify_section("Sword", "C", "Weapon / Sword") == "gear"
    assert classify_section("Adena", "NG", "Money") == "other"
    assert classify_section("Quest Item", "NG", "Quest Item / X") == "excluded"


def test_sealed_base_name():
    assert sealed_base_name("Sealed Blue Wolf Boots") == "Blue Wolf Boots"
    assert sealed_base_name("Blue Wolf Boots") is None
