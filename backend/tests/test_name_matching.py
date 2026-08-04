from services.name_matching import (
    clean_display_name,
    is_recipe_name,
    normalize_product_name,
    unescape_text,
)


def test_unescape_html_entities():
    assert unescape_text("Arcsmith&#039;s Anvil") == "Arcsmith's Anvil"
    assert unescape_text("A &amp; B") == "A & B"
    assert unescape_text("Plain Name") == "Plain Name"


def test_clean_display_name_unescapes():
    assert clean_display_name("Arcsmith&#039;s Anvil") == "Arcsmith's Anvil"
    assert clean_display_name("Lu4 Wiki: Item Arcsmith&#039;s Anvil") == "Arcsmith's Anvil"


def test_normalize_product_name_drops_apostrophes():
    assert normalize_product_name("Arcsmith&#039;s Anvil") == "arcsmiths anvil"
    assert normalize_product_name("Butcher's Sword") == normalize_product_name("Butchers Sword")
    assert normalize_product_name("Conjurer's Knife") == normalize_product_name("Conjurers Knife")
    assert normalize_product_name("Conjuror's Staff Head") == normalize_product_name(
        "Conjurors Staff Head"
    )


def test_normalize_keeps_recipe_prefix():
    assert normalize_product_name("Recipe: Soulshot (D-Grade)").startswith("recipe:")
    assert not normalize_product_name("Soulshot (D-Grade)").startswith("recipe:")
    assert normalize_product_name("Recipe: Soulshot (D-Grade)") != normalize_product_name(
        "Soulshot (D-Grade)"
    )


def test_normalize_unifies_grade_spellings():
    assert normalize_product_name("Recipe: Spiritshot D") == "recipe: spiritshot (d-grade)"
    assert normalize_product_name("Recipe: Spiritshot (D-Grade)") == "recipe: spiritshot (d-grade)"
    assert normalize_product_name("Recipe: Spiritshot (D)") == "recipe: spiritshot (d-grade)"
    assert normalize_product_name("Recipe: Spiritshot D") != normalize_product_name(
        "Recipe: Spiritshot C"
    )
    assert normalize_product_name("Soulshot (D-Grade) D") == "soulshot (d-grade)"
    assert normalize_product_name("Recipe: Soulshot (D-Grade) NG") == "recipe: soulshot (d-grade)"


def test_normalize_strips_optional_package_and_level_suffixes():
    assert normalize_product_name(
        "Recipe: Spiritshot (D) Compressed Package"
    ) == normalize_product_name("Recipe: Spiritshot (D) Compressed Package (100%)")
    assert normalize_product_name("Elixir of MP (D-Grade) 20-39") == normalize_product_name(
        "Elixir of MP (D-Grade)"
    )
    assert normalize_product_name("Elixir of HP (D-Grade) 20-39") == "elixir of hp (d-grade)"


def test_is_recipe_name():
    assert is_recipe_name("Recipe: Soulshot (D-Grade)") is True
    assert is_recipe_name("Lu4 Wiki: Item Recipe: Soulshot (D-Grade)") is True
    assert is_recipe_name("Soulshot (D-Grade)") is False
