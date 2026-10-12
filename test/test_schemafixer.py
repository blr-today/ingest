from src.processors.schemafixer import EDGES


def clean(name):
    return EDGES.sub("", name) or name


def test_strips_edge_emoji():
    assert (
        clean("💬 THURSTALK #01: WHY MUSIC MOVES US")
        == "THURSTALK #01: WHY MUSIC MOVES US"
    )
    assert (
        clean("🌠 Astro-Photography Exhibition-4.0 🌠")
        == "Astro-Photography Exhibition-4.0"
    )
    assert clean("￼SHORT CIRCUIT 3.0") == "SHORT CIRCUIT 3.0"


def test_keeps_inner_symbols_and_emoji_only_names():
    assert clean("Rock ★ Night 🎸 Live") == "Rock ★ Night 🎸 Live"
    assert clean("🎉🎉") == "🎉🎉"
