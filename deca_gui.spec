# -*- mode: python -*-

block_cipher = None

added_files = [
    ('resources/*.txt', 'resources/'),
    ('resources/gz', 'resources/gz'),
    ('resources/gzb', 'resources/gzb'),
    ('resources/hp', 'resources/hp'),
    ('resources/ghidra_strings', 'resources/ghidra_strings'),
    ('tool_resources/make_web_map', 'tool_resources/make_web_map'),
    ('extern/HavokLib/build/_bin2xml/bin2xml*', 'extern/HavokLib/build/_bin2xml/),
]

a = Analysis(
    ['entry_point.py'],
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
