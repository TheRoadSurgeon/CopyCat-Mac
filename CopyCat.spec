# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['mac/mac_main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('copycat_status.png', '.')],
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
    name='CopyCat',
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
    icon=['build_icon/CopyCat.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CopyCat',
)
app = BUNDLE(
    coll,
    name='CopyCat.app',
    icon='build_icon/CopyCat.icns',
    bundle_identifier='com.yourteam.copycat',
)
