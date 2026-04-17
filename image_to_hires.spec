# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).resolve()
realcugan_bin_dir = project_root / "bin" / "realcugan"
realcugan_models_dir = project_root / "models" / "realcugan" / "models-se"


def _collect_tree(source_dir: Path, target_prefix: str) -> list[tuple[str, str]]:
    return [
        (str(path), f"{target_prefix}/{path.relative_to(source_dir).parent}".rstrip("/."))
        for path in sorted(source_dir.rglob("*"))
        if path.is_file()
    ]


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
