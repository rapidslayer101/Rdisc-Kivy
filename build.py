from os import system, getcwd, remove
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from enclib import hash_a_file

with open("sha.txt", encoding="utf-8") as f:
    latest_sha, version, tme, bld_num, run_num = f.readlines()[-1].split("§")
    print(latest_sha, version, tme, bld_num, run_num)
    release_major, major, build, run = version.replace("V", "").split(".")

is_major = input("Major y/n: ")
if is_major.lower() == "y":
    major = int(major) + 1
    build = 0
    run = 0
else:
    build = int(build) + 1
    run = 0
with open("rdisc.spec", "w", encoding="utf-8") as f:
    f.write("""# -*- mode: python ; coding: utf-8 -*-
from kivy_deps import sdl2, glew


block_cipher = None


a = Analysis(
    ['rdisc.py'],
    pathex=['%s'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    name='%s',
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
    icon='rdisc.ico',
)
""" % (getcwd().replace("\\", "/"), f'rdisc-{release_major}.{major}.{build}.{run}'))


system("python -m PyInstaller rdisc.spec")
hashed = hash_a_file(f"dist/rdisc-{release_major}.{major}.{build}.{run}.exe")

if latest_sha == hashed:
    print("This build is identical to the previous, no changes to sha.txt have been made")
else:
    with open("sha.txt", "a+", encoding="utf-8") as f:
        tme = str(datetime.now())[:-4].replace(' ', '_')
        print(f"{hashed}§V{release_major}.{major}.{build}.{run}§TME-{tme}"
              f"§BLD_NM-{int(bld_num[7:])+1}§RUN_NM-{run_num[7:]}")
        f.write(f"\n{hashed}§V{release_major}.{major}.{build}.{run}§TME-{tme}"
                f"§BLD_NM-{int(bld_num[7:])+1}§RUN_NM-{run_num[7:]}")
    ZipFile(f"dist/rdisc-{release_major}.{major}.{build}.{run}.zip", "w", ZIP_DEFLATED)\
        .write("dist/" + f"rdisc-{release_major}.{major}.{build}.{run}.exe",
               arcname=f"rdisc-{release_major}.{major}.{build}.{run}.exe")
    with open("dist/latest_hash.txt", "w", encoding="utf-8") as f:
        f.write(hashed)
    remove(f"dist/rdisc-{release_major}.{major}.{build}.{run}.exe")
    if is_major.lower() == "n":
        for i in range(0, build):
            try:
                remove(f"dist/rdisc-{release_major}.{major}.{i}.{run}.zip")
            except FileNotFoundError:
                pass
    print(f"Build V{release_major}.{major}.{build}.{run} Completed")
