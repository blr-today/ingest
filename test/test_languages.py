from src.processors.languages import LANGUAGE_MAP, SCRIPTS, ScriptLanguage


def lang(name, **event):
    return ScriptLanguage.process("u", {"name": name, **event}).get("inLanguage")


def test_script_names_language():
    assert lang("ಕನ್ನಡ ರಾಜ್ಯೋತ್ಸವ") == "kn"
    assert lang("हिंदी कवि सम्मेलन", inLanguage="en") == "hi"
    assert lang("தமிழ் நாடகம் 2026", inLanguage="") == "ta"
    assert lang("മലയാളം") == "ml"


def test_latin_titles_and_known_languages_are_kept():
    assert lang("Kannada Rajyotsava ಕನ್ನಡ") is None
    assert lang("ಕನ್ನಡ", inLanguage="hi") == "hi"
    assert lang("2026 !!") is None
    assert ScriptLanguage.process("u", {"name": None}) == {"name": None}


def test_maps_agree():
    assert set(SCRIPTS) <= set(LANGUAGE_MAP.values())
