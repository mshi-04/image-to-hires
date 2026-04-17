# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).resolve()
realcugan_bin_dir = project_root / "bin" / "realcugan"
realcugan_models_dir = project_root / "models" / "realcugan" / "models-se"


def _normalize_target_prefix(target_prefix: str) -> str:
    if target_prefix.endswith("/") or target_prefix.endswith("."):
        return target_prefix[:-1]
    return target_prefix


def _collect_tree(source_dir: Path, target_prefix: str) -> list[tuple[str, str]]:
    normalized_target_prefix = _normalize_target_prefix(target_prefix)
    if not source_dir.exists():
        raise FileNotFoundError(
            f"Required asset directory is missing: {source_dir} (target: {normalized_target_prefix})"
        )
    if not source_dir.is_dir():
        raise RuntimeError(
            f"Expected a directory for assets but found a non-directory path: {source_dir} "
            f"(target: {normalized_target_prefix})"
        )

    collected: list[tuple[str, str]] = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue

        relative_parent = path.relative_to(source_dir).parent
        destination = normalized_target_prefix
        if relative_parent != Path("."):
            destination = f"{normalized_target_prefix}/{relative_parent.as_posix()}"
        collected.append((str(path), destination))

    if not collected:
        raise FileNotFoundError(
            f"No files found to bundle from directory: {source_dir} "
            f"(target: {normalized_target_prefix})"
        )

    return collected


datas = []
datas.extend(_collect_tree(realcugan_bin_dir, "bin/realcugan"))
datas.extend(_collect_tree(realcugan_models_dir, "models/realcugan/models-se"))

a = Analysis(
    [str(project_root / "src" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="image-to-hires",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="image-to-hires",
)
