import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "hooks" / "memory_flags.py"


def load_flags_module():
    spec = importlib.util.spec_from_file_location("memory_flags", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MemoryFlagsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.flags = load_flags_module()

    def test_memory_feature_defaults_off(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.flags.memory_enabled())

    def test_memory_feature_only_accepts_explicit_opt_in_values(self) -> None:
        for value in ["1", "true", "TRUE", "yes", "on"]:
            with self.subTest(value=value), patch.dict(os.environ, {"DOTFILES_MEMORY_ENABLED": value}, clear=True):
                self.assertTrue(self.flags.memory_enabled())

        for value in ["", "0", "false", "no", "off", "unexpected"]:
            with self.subTest(value=value), patch.dict(os.environ, {"DOTFILES_MEMORY_ENABLED": value}, clear=True):
                self.assertFalse(self.flags.memory_enabled())


if __name__ == "__main__":
    unittest.main()
