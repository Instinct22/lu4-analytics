"""Tests for NPC buy price derivation."""

from calculations.npc_prices import compute_npc_buy, is_npc_buy_eligible


def test_npc_buy_d_armor():
    assert compute_npc_buy(114850, "D", "armors/heavy/upper") == 275640


def test_npc_buy_ng_weapon():
    assert compute_npc_buy(1000, "NG", "weapons/sword") == 2400


def test_npc_buy_ng_jewelry():
    assert is_npc_buy_eligible("NG", "other/jewelry/earring")
    assert compute_npc_buy(500, "NG", "other/jewelry/earring") == 1200


def test_npc_buy_excludes_c_grade():
    assert compute_npc_buy(114850, "C", "armors/heavy/upper") is None


def test_npc_buy_excludes_materials():
    assert compute_npc_buy(1000, "NG", "materials/other") is None


def test_npc_buy_requires_npc_sell():
    assert compute_npc_buy(None, "D", "weapons/sword") is None
