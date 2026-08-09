"""Static fallback prices for craft materials."""

from calculations.static_prices import resolve_avg_price, static_avg_price


def test_gemstone_static_prices():
    assert static_avg_price(2130) == 1200
    assert static_avg_price(2131) == 3600
    assert static_avg_price(2132) == 12000
    assert static_avg_price(2133) == 36000
    assert static_avg_price(57) is None


def test_resolve_avg_price_prefers_static():
    assert resolve_avg_price(2130, 999.0) == 1200
    assert resolve_avg_price(57, 150.0) == 150.0
    assert resolve_avg_price(57, None) is None
