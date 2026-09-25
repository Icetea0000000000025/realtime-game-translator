# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import site
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

project_dir = os.path.abspath(SPECPATH)

# 1. Collect Data Files
datas = [
    (os.path.join(project_dir, 'config.json'), '.'),
    (os.path.join(project_dir, 'glossary.json'), '.'),
    (os.path.join(project_dir, 'app_icon.ico'), '.'),
]

# Package data
datas += collect_data_files('faster_whisper')
datas += collect_data_files('_sounddevice_data')

# 2. Collect Dynamic Libraries (DLLs)
binaries = []
binaries += collect_dynamic_libs('ctranslate2')
binaries += collect_dynamic_libs('_sounddevice_data')

try:
    binaries += collect_dynamic_libs('pyaudiowpatch')
except Exception:
    pass

# We only need cuBLAS for CTranslate2 GPU execution (cublas64_12.dll & cublasLt64_12.dll)
# We strictly exclude the giant cudnn engine DLLs (>1.5 GB) & nvrtc which are not used by CTranslate2.
venv_sp = os.path.join(project_dir, '.venv', 'Lib', 'site-packages')
cublas_bin = os.path.join(venv_sp, 'nvidia', 'cublas', 'bin')
if os.path.isdir(cublas_bin):
    for f in ['cublas64_12.dll', 'cublasLt64_12.dll']:
        fpath = os.path.join(cublas_bin, f)
        if os.path.isfile(fpath):
            binaries.append((fpath, '.'))

# 3. Hidden Imports
hidden_imports = [
    'live_translation',
    'live_translation.sessions',
    'live_translation.text_pipeline',
    'live_translation.translators',
    'faster_whisper',
    'ctranslate2',
    'sounddevice',
    '_sounddevice_data',
    'pyaudiowpatch',
    'deep_translator',
    'translatepy',
    'google.genai',
    'dotenv',
    'requests',
    'urllib3',
    'charset_normalizer',
    'idna',
    'certifi',
    'numpy',
    'tkinter',
    'tkinter.ttk',
    'queue',
    'threading',
    'ctypes',
    'json',
]

hidden_imports += collect_submodules('faster_whisper')
hidden_imports += collect_submodules('ctranslate2')
hidden_imports += collect_submodules('live_translation')

# Exclude unnecessary heavy packages, cuDNN engines, and nvrtc to keep file size well under 2GB
excludes = [
    'matplotlib', 'scipy', 'pandas', 'IPython', 'notebook', 'pytest',
    'nvidia.cudnn', 'nvidia.cuda_nvrtc', 'nvidia.cuda_cupti', 'nvidia.cuda_nvcc',
    'nvidia.cufft', 'nvidia.curand', 'nvidia.cusolver', 'nvidia.cusparse',
    'nvidia.nccl', 'nvidia.nvjitlink', 'nvidia.nvtx',
    'torch', 'torchaudio', 'torchvision', 'cv2',
]

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Deduplicate DLLs and filter out any heavy unneeded cuDNN engines (>1.5 GB saved!)
filtered_binaries = []
seen_dlls = set()
EXCLUDED_DLL_PREFIXES = ('cudnn_adv', 'cudnn_engines', 'cudnn_ops', 'cudnn_graph', 'cudnn_heuristic', 'nvrtc')

for dest, src, typ in a.binaries:
    base = os.path.basename(dest).lower()
    if any(base.startswith(prefix) for prefix in EXCLUDED_DLL_PREFIXES):
        continue
    if base.endswith('.dll') or base.endswith('.pyd'):
        if base in seen_dlls:
            continue
        seen_dlls.add(base)
    filtered_binaries.append((dest, src, typ))

a.binaries = filtered_binaries

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Main Windowed App (Sleek, no black console window)
exe_gui = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RealtimeGameTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(project_dir, 'app_icon.ico'),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Debug version with Console window
exe_debug = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RealtimeGameTranslator_Debug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=os.path.join(project_dir, 'app_icon.ico'),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_gui,
    exe_debug,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='RealtimeGameTranslator',
)
