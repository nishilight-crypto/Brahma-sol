# -*- mode: python ; coding: utf-8 -*-
import os
import sys

cwd = os.path.abspath(os.getcwd())
if not os.path.exists(os.path.join(cwd, 'installer')):
    cwd = os.path.abspath(os.path.join(os.getcwd(), '..'))

datas = [
    (os.path.join(cwd, 'installer', 'html'), os.path.join('installer', 'html')),
    (os.path.join(cwd, 'assets', 'brahma_sol_logo.ico'), 'assets')
]

# Bundle newly built BrahmaSol application directory as payload
source_dist = os.path.join(cwd, 'dist', 'BrahmaSol')
if os.path.exists(source_dist):
    datas.append((source_dist, 'BrahmaSol'))
else:
    # Fallback to source root
    datas.append((cwd, 'BrahmaSol'))

a = Analysis(
    [os.path.join(cwd, 'installer', 'install_wizard.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
        'shutil',
        'win32com.client',
        'winreg'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

ico_target = os.path.join(cwd, 'assets', 'brahma_sol_logo.ico')
if not os.path.exists(ico_target):
    ico_target = os.path.join(cwd, 'assets', 'brahma_evo_logo.ico')
if not os.path.exists(ico_target):
    ico_target = None

ver_target = os.path.join(cwd, 'version_setup_brahma_sol.txt')

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='brahma-sol_setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=ico_target,
    version=ver_target if os.path.exists(ver_target) else None
)
