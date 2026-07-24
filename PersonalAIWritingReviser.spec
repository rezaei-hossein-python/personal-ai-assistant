# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path.cwd()
conda_library_bin = project_root / ".conda" / "Library" / "bin"

a = Analysis(
    ["desktop/writing_reviser_main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
        "webview",
        "uvicorn",
        "fastapi",
        "sqlalchemy",
        "alembic",
        "frontend",
        "openai",
    ],
    noarchive=False,
    optimize=0,
)

openssl_dll_names = {"libssl-3-x64.dll", "libcrypto-3-x64.dll"}
a.binaries = [
    binary for binary in a.binaries if binary[0].lower() not in openssl_dll_names
]
for dll_name in sorted(openssl_dll_names):
    a.binaries.append((dll_name, str(conda_library_bin / dll_name), "BINARY"))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PersonalAIWritingReviser",
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
    name="PersonalAIWritingReviser",
)
