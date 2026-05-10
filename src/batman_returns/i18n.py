"""Tiny string-table i18n. Routes UI labels through ``t()`` so that switching
``save.language`` updates rendered text live.

Usage::

    from .i18n import t, set_language
    set_language("es")
    label = t("score")  # → "PUNTOS"

Keys missing from a translation table fall back to English (and finally to
the key itself), so untranslated strings still render.
"""

from __future__ import annotations

EN: dict[str, str] = {
    # HUD
    "score": "SCORE",
    "lives": "LIVES",
    "bat":   "BAT",
    "combo": "COMBO",
    "first_blood": "FIRST BLOOD!",
    "charged": "CHARGED!",
    "recatch": "RECATCH",
    # Title menu
    "new_game":     "NEW GAME",
    "new_game_plus": "NEW GAME +",
    "continue":     "CONTINUE",
    "stage_select": "STAGE SELECT",
    "settings":     "SETTINGS",
    "high_scores":  "HIGH SCORES",
    "quit":         "QUIT",
    # Settings
    "difficulty":  "DIFFICULTY",
    "sfx_volume":  "SFX VOLUME",
    "music_volume": "MUSIC VOLUME",
    "show_fps":    "SHOW FPS",
    "language":    "LANGUAGE",
    "reset_high_scores": "RESET HIGH SCORES",
    "back":        "BACK",
    # Pause
    "paused":      "PAUSED",
    "resume":      "RESUME",
    "controls":    "CONTROLS",
    "quit_to_title": "QUIT TO TITLE",
    # State screens
    "stage_clear": "STAGE CLEAR!",
    "press_enter_to_continue": "PRESS ENTER TO CONTINUE",
    "kills":       "KILLS",
    "time":        "TIME",
    "max_combo":   "MAX COMBO",
    "no_damage_bonus": "NO-DAMAGE BONUS",
    "total":       "TOTAL",
    "game_over":   "GAME OVER",
    "victory":     "GOTHAM IS SAFE",
    # Stage names
    "stage_1": "GOTHAM STREETS",
    "stage_2": "GOTHAM ROOFTOPS",
    "stage_3": "THE SEWERS",
    "stage_4": "ICE PLAZA",
    "stage_5": "HARBOR DOCKS",
    "stage_6": "ARKHAM ASYLUM",
    "stage_7": "PENGUIN'S LAIR",
    "stage_8": "THE BATCAVE",
}

ES: dict[str, str] = {
    "score":        "PUNTOS",
    "lives":        "VIDAS",
    "bat":          "BAT",
    "combo":        "COMBO",
    "first_blood":  "PRIMERA SANGRE!",
    "charged":      "CARGADO!",
    "recatch":      "RECOGIDO",
    "new_game":     "NUEVA PARTIDA",
    "new_game_plus": "PARTIDA NUEVA +",
    "continue":     "CONTINUAR",
    "stage_select": "SELECCIONAR FASE",
    "settings":     "OPCIONES",
    "high_scores":  "MEJORES PUNTOS",
    "quit":         "SALIR",
    "difficulty":   "DIFICULTAD",
    "sfx_volume":   "VOLUMEN SFX",
    "music_volume": "VOLUMEN MUSICA",
    "show_fps":     "MOSTRAR FPS",
    "language":     "IDIOMA",
    "reset_high_scores": "BORRAR PUNTOS",
    "back":         "VOLVER",
    "paused":       "PAUSA",
    "resume":       "REANUDAR",
    "controls":     "CONTROLES",
    "quit_to_title": "VOLVER AL TITULO",
    "stage_clear":  "FASE COMPLETADA!",
    "press_enter_to_continue": "PULSA ENTER PARA CONTINUAR",
    "kills":        "BAJAS",
    "time":         "TIEMPO",
    "max_combo":    "COMBO MAX",
    "no_damage_bonus": "BONUS SIN DANO",
    "total":        "TOTAL",
    "game_over":    "FIN DEL JUEGO",
    "victory":      "GOTHAM ESTA A SALVO",
    "stage_1":      "CALLES DE GOTHAM",
    "stage_2":      "TEJADOS DE GOTHAM",
    "stage_3":      "LAS CLOACAS",
    "stage_4":      "PLAZA DE HIELO",
    "stage_5":      "MUELLE",
    "stage_6":      "MANICOMIO ARKHAM",
    "stage_7":      "GUARIDA DEL PINGUINO",
    "stage_8":      "LA BATICUEVA",
}

TABLES: dict[str, dict[str, str]] = {"en": EN, "es": ES}

_current_lang = "en"


def set_language(lang: str) -> None:
    global _current_lang
    if lang in TABLES:
        _current_lang = lang


def get_language() -> str:
    return _current_lang


def t(key: str) -> str:
    """Look up the translated string for ``key``. Falls back to English then key."""
    table = TABLES.get(_current_lang, EN)
    return table.get(key) or EN.get(key) or key
