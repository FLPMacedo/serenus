# -*- mode: python ; coding: utf-8 -*-
#
# serenus.spec — PyInstaller spec do Serenus
#
# Como gerar o executável:
#   pyinstaller serenus.spec
#
# O executável final estará em: dist/Serenus.exe

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Recursos estáticos — extraídos para sys._MEIPASS em runtime
        (str(ROOT / "imagens" / "logo.png"),      "imagens"),
        (str(ROOT / "imagens" / "logo.ico"),      "imagens"),
        (str(ROOT / "imagens" / "visa.png"),      "imagens"),
        (str(ROOT / "imagens" / "mastercad.png"), "imagens"),
    ],
    hiddenimports=[
        "customtkinter",
        "PIL._tkinter_finder",
        "openpyxl.styles.builtins",
        "matplotlib.backends.backend_tkagg",
        "views.widgets.ajuda",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "google",
        "google_auth_oauthlib",
        "googleapiclient",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Serenus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "imagens" / "logo.ico"),
    version_file=None,
)
