from __future__ import annotations

import os


ENABLED_VALUES = {"1", "true", "yes", "on"}


def memory_enabled(env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return source.get("DOTFILES_MEMORY_ENABLED", "").strip().lower() in ENABLED_VALUES
