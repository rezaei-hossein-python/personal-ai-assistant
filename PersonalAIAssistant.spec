# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path.cwd()
frontend_dist = project_root / "frontend" / "dist"
conda_bin = project_root / ".conda" / "Library" / "bin"

a = Analysis(
    ["desktop/main.py"],
    pathex=[str(project_root)],
    binaries=[
        (str(conda_bin / "libssl-3-x64.dll"), "."),
        (str(conda_bin / "libcrypto-3-x64.dll"), "."),
    ],
    datas=[
        (str(frontend_dist), "frontend_dist"),
    ],
    hiddenimports=[
        "keyring.backends.Windows",
        "webview",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PersonalAIAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PersonalAIAssistant",
)
