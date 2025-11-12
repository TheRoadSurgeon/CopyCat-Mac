# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# Make sure PyInstaller sees your project root so 'core', 'ui', 'utils' imports work
pathex = [os.path.abspath(".")]

a = Analysis(
    ['mac/mac_main.py'],
    pathex=pathex,
    binaries=[],
    datas=[
        ('copycat_status.png', '.'),  # tray/menu-bar icon packed into app
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CopyCat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowless
    disable_windowed_traceback=False,
    target_arch=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CopyCat',
)

app = BUNDLE(
    coll,
    name='CopyCat.app',
    icon='build_icon/CopyCat.icns',
    bundle_identifier='com.yourteam.copycat',
    info_plist={
        'LSUIElement': True,                 # <-- no Dock, menu-bar only
        'CFBundleName': 'CopyCat',
        'CFBundleDisplayName': 'CopyCat',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
    },
)
