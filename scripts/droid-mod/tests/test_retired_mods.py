import importlib.util
import unittest
from pathlib import Path


ROOT = Path("/Users/zhenninglang/.dotfiles/scripts/droid-mod")
RETIRED_MOD = "mod-unlock-max-custom-effort"


def _load_apply_module():
    spec = importlib.util.spec_from_file_location("droid_mod_apply", ROOT / "apply.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RetiredModsTests(unittest.TestCase):
    def test_unlock_max_custom_effort_is_not_an_active_mod(self) -> None:
        apply = _load_apply_module()

        self.assertNotIn(RETIRED_MOD, {mod["key"] for mod in apply.MODS})
        self.assertNotIn(RETIRED_MOD, apply.MOD_KEYS)
        self.assertNotIn(RETIRED_MOD, (ROOT / "status.py").read_text())
        self.assertFalse((ROOT / "mods" / "mod_unlock_max_custom_effort.py").exists())


if __name__ == "__main__":
    unittest.main()
