# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=['e:\\\\Dev_maison\\\\bot-project-creator'],  # Ajout du chemin racine du projet
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('src/config/best_system_prompts.json', 'src/config')  # Ajout du fichier de configuration
    ],
    hiddenimports=[
        'webview',  # Nécessaire pour pywebview
        'cefpython3',  # Pour CEF (Chromium Embedded Framework)
        # 'webview.platforms.edgechromium', # Commentez ou supprimez si vous utilisez principalement CEF
        # 'webview.platforms.winforms',     # Commentez ou supprimez si vous utilisez principalement CEF
        'run', # Assurez-vous que votre script run.py est trouvable
        'engineio.async_drivers.threading', # Souvent requis pour Flask-SocketIO
        # Ajoutez d'autres imports cachés si nécessaire après des tests
    ],
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
    a.binaries,
    a.datas,
    [],
    name='MorphAius', 
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Correct pour une application GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/images/favicon.ico'  # Assurez-vous que favicon.ico existe à cet emplacement
)
