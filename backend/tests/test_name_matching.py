from services.name_matching import clean_display_name, normalize_product_name, unescape_text


def test_unescape_html_entities():
    assert unescape_text("Arcsmith&#039;s Anvil") == "Arcsmith's Anvil"
    assert unescape_text("A &amp; B") == "A & B"
    assert unescape_text("Plain Name") == "Plain Name"


def test_clean_display_name_unescapes():
    assert clean_display_name("Arcsmith&#039;s Anvil") == "Arcsmith's Anvil"
    assert clean_display_name("Lu4 Wiki: Item Arcsmith&#039;s Anvil") == "Arcsmith's Anvil"


def test_normalize_product_name_unescapes():
    assert normalize_product_name("Arcsmith&#039;s Anvil") == "arcsmith's anvil"
