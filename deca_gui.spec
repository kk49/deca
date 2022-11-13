# -*- mode: python -*-

block_cipher = None

added_files = [
    ('resources/deca/*.txt', 'resources/deca/'),
    ('resources/deca/adf', 'resources/deca/adf'),
    ('resources/deca/an', 'resources/deca/an'),
    ('resources/deca/field_strings', 'resources/deca/field_strings'),
    ('resources/deca/gameinfo', 'resources/deca/gameinfo'),
    ('resources/deca/ghidra_strings', 'resources/deca/ghidra_strings'),
    ('resources/deca/gz', 'resources/deca/gz'),
    ('resources/deca/gzb', 'resources/deca/gzb'),
    ('resources/deca/hp', 'resources/deca/hp'),
    ('resources/deca/jc4', 'resources/deca/jc4'),
    ('resources/deca/rg2', 'resources/deca/rg2'),
    ('resources/make_web_map', 'resources/make_web_map'),
    ('root', 'root'),
]

a = Analysis(
    ['python/deca_gui/deca_gui/entry_point.py'],
    pathex=['/home/krys/prj/deca'],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='deca_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True )

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='deca_gui')
