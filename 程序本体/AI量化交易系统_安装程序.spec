# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['_installer_temp\\setup_source\\install.py'],
    pathex=[],
    binaries=[],
    datas=[('_internal', '.'), ('install.py', '.'), ('uninstall.ps1', '.')],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.filedialog'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['win32com'],
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
    name='AI量化交易系统_安装程序',
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
)
