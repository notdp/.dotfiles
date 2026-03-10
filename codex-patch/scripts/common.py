#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path

DEFAULT_REPO = Path.home() / "Developer" / "codex"
DEFAULT_OFFICIAL_BIN = Path("/opt/homebrew/bin/codex")
VERSION_PATTERN = re.compile(r"codex-cli\s+([^\s]+)")
PATCH_ASSETS = [
    ("0.112.", "rust-v0.112.x-colorfgbg.patch"),
    ("0.0.0", "tmux-cc-colorfgbg.patch"),
]
TARGET_MARKERS = [
    (
        "0.112.",
        {
            "codex-rs/tui/src/terminal_palette.rs": [
                "colorfgbg_default_colors",
                "tmux_control_mode()",
            ],
            "codex-rs/Cargo.toml": [
                'lto = "thin"',
                "codegen-units = 16",
            ],
        },
    ),
    (
        "0.0.0",
        {
            "codex-rs/tui/src/terminal_palette.rs": [
                "colorfgbg_default_colors",
                "tmux_control_mode()",
            ],
            "codex-rs/tui2/src/terminal_palette.rs": [
                "colorfgbg_default_colors",
                "tmux_control_mode()",
            ],
        },
    ),
]
TARGET_SETS = [
    (
        "0.112.",
        [
            "codex-rs/tui/src/terminal_palette.rs",
            "codex-rs/Cargo.toml",
        ],
    ),
    (
        "0.0.0",
        [
            "codex-rs/tui/src/terminal_palette.rs",
            "codex-rs/tui2/src/terminal_palette.rs",
        ],
    ),
]


def patch_home() -> Path:
    return Path(__file__).resolve().parents[1]


def assets_dir() -> Path:
    return patch_home() / "assets"


def state_dir() -> Path:
    path = patch_home() / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def manifest_path() -> Path:
    return state_dir() / "manifest.json"


def resolve_repo(raw: str | None) -> Path:
    base = Path(raw).expanduser() if raw else DEFAULT_REPO
    return base.resolve()


def ensure_repo(repo: Path) -> None:
    if not (repo / ".git").exists():
        raise SystemExit(f"错误: 不是 git 仓库: {repo}")
    targets = repo_targets(repo)
    missing = [target for target in targets if not (repo / target).exists()]
    if missing:
        joined = "\n".join(f"  - {item}" for item in missing)
        raise SystemExit(f"错误: 仓库缺少目标文件:\n{joined}")


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "(无输出)"
        raise SystemExit(f"命令失败: {' '.join(cmd)}\n{detail}")
    return proc


def file_text(repo: Path, relative_path: str) -> str:
    return (repo / relative_path).read_text()


def target_markers_for_version(version: str) -> dict[str, list[str]]:
    for prefix, target_markers in TARGET_MARKERS:
        if version.startswith(prefix):
            return target_markers
    raise SystemExit(
        f"错误: 当前没有可用的补丁检测规则来匹配 Codex 版本 {version}。"
    )


def is_applied(repo: Path) -> bool:
    target_markers = target_markers_for_version(repo_workspace_version(repo))
    for target in repo_targets(repo):
        markers = target_markers.get(target)
        if not markers:
            raise SystemExit(f"错误: 目标文件 {target} 缺少补丁检测规则。")
        text = file_text(repo, target)
        for marker in markers:
            if marker not in text:
                return False
    return True


def target_status(repo: Path) -> list[str]:
    proc = run(["git", "status", "--short", "--", *repo_targets(repo)], cwd=repo, check=True)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def branch(repo: Path) -> str:
    proc = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, check=True)
    return proc.stdout.strip()


def revision(repo: Path) -> str:
    proc = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, check=True)
    return proc.stdout.strip()


def full_revision(repo: Path) -> str:
    proc = run(["git", "rev-parse", "HEAD"], cwd=repo, check=True)
    return proc.stdout.strip()


def binary_path(repo: Path, release: bool) -> Path:
    profile = "release" if release else "debug"
    return repo / "codex-rs" / "target" / profile / "codex"


def build(repo: Path, release: bool) -> Path:
    cmd = ["cargo", "build", "-p", "codex-cli"]
    if release:
        cmd.append("--release")
    run(cmd, cwd=repo / "codex-rs", check=True)
    return binary_path(repo, release)


def print_status_lines(lines: list[str]) -> None:
    if not lines:
        print("目标文件工作树: 干净")
        return
    print("目标文件工作树:")
    for line in lines:
        print(f"  {line}")


def warn_and_exit(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def repo_workspace_version(repo: Path) -> str:
    cargo_toml = repo / "codex-rs" / "Cargo.toml"
    data = tomllib.loads(cargo_toml.read_text())
    return str(data["workspace"]["package"]["version"])


def patch_path_for_version(version: str) -> Path:
    for prefix, filename in PATCH_ASSETS:
        if version.startswith(prefix):
            return assets_dir() / filename
    raise SystemExit(
        f"错误: 当前没有可用的 patch 资产来匹配 Codex 版本 {version}。"
    )


def release_ref(version: str) -> str:
    return f"rust-v{version}"


def targets_for_version(version: str) -> list[str]:
    for prefix, targets in TARGET_SETS:
        if version.startswith(prefix):
            return targets
    raise SystemExit(
        f"错误: 当前没有可用的目标文件集合来匹配 Codex 版本 {version}。"
    )


def repo_targets(repo: Path) -> list[str]:
    return targets_for_version(repo_workspace_version(repo))


def official_bin_path() -> Path | None:
    override = os.environ.get("CODEX_OFFICIAL_BIN")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    candidates.append(DEFAULT_OFFICIAL_BIN)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def codex_version(binary: Path) -> str | None:
    proc = subprocess.run(
        [str(binary), "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    output = proc.stdout.strip() or proc.stderr.strip()
    match = VERSION_PATTERN.search(output)
    if not match:
        return None
    return match.group(1)


def official_version() -> tuple[Path | None, str | None]:
    binary = official_bin_path()
    if binary is None:
        return None, None
    return binary, codex_version(binary)


def load_manifest() -> dict[str, object] | None:
    path = manifest_path()
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_manifest(data: dict[str, object]) -> None:
    path = manifest_path()
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def build_manifest(
    repo: Path,
    source_ref: str,
    patch_path: Path,
    binary: Path,
    official_binary: Path | None,
    official_version_value: str | None,
) -> dict[str, object]:
    return {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "built_binary": str(binary),
        "built_binary_version": codex_version(binary),
        "official_binary": str(official_binary) if official_binary else None,
        "official_version": official_version_value,
        "patch_asset": str(patch_path),
        "repo_path": str(repo),
        "repo_workspace_version": repo_workspace_version(repo),
        "source_branch": branch(repo),
        "source_commit": full_revision(repo),
        "source_ref": source_ref,
    }


def manifest_update_reason(repo: Path) -> str | None:
    manifest = load_manifest()
    if manifest is None:
        return "manifest 不存在"

    official_binary, official_version_value = official_version()
    if official_version_value is None:
        return "无法读取官方 codex 版本"

    if manifest.get("official_version") != official_version_value:
        return (
            f"官方 codex 已从 {manifest.get('official_version')} 升级到 {official_version_value}"
        )

    if manifest.get("official_binary") and official_binary:
        if Path(str(manifest["official_binary"])).resolve() != official_binary:
            return "官方 codex 路径变化"

    binary_value = manifest.get("built_binary")
    if not binary_value:
        return "manifest 缺少 built_binary"

    binary = Path(str(binary_value))
    if not binary.exists():
        return "manifest 记录的 patched binary 不存在"

    binary_version = codex_version(binary)
    if manifest.get("built_binary_version") != binary_version:
        return "patched binary 版本与 manifest 不一致"

    repo_version = repo_workspace_version(repo)
    if manifest.get("repo_workspace_version") != repo_version:
        return "仓库源码版本与 manifest 不一致"

    if Path(str(manifest.get("repo_path", ""))) != repo:
        return "manifest 记录的仓库路径与当前不一致"

    return None
