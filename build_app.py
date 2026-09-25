#!/usr/bin/env python3
"""
build_app.py - Automated packaging and distribution tool for Realtime Game Translator.

This script:
1. Generates the high-res app icon (app_icon.ico)
2. Compiles the project using PyInstaller (onedir mode with CUDA support)
3. Prepares the dist/RealtimeGameTranslator release folder
4. Generates a Portable ZIP archive ready for GitHub Releases
5. Generates an Inno Setup script (installer.iss) for creating Setup.exe
"""

import os
import sys
import shutil
import zipfile
import subprocess
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
APP_OUT_DIR = os.path.join(DIST_DIR, "RealtimeGameTranslator")

def log(msg):
    print(f"\n[BUILD] {'='*50}\n[BUILD] {msg}\n[BUILD] {'='*50}")

def step(msg):
    print(f"[*] {msg}")

def ensure_icon():
    icon_path = os.path.join(PROJECT_DIR, "app_icon.ico")
    if not os.path.exists(icon_path):
        step("Generating app_icon.ico...")
        try:
            import create_icon
            create_icon.create_app_icon(icon_path)
        except Exception as e:
            step(f"Warning: Failed to generate icon: {e}")

def clean_previous_build():
    step("Cleaning previous build artifacts...")
    for d in [APP_OUT_DIR, os.path.join(PROJECT_DIR, "build")]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

def run_pyinstaller():
    log("Running PyInstaller Build...")
    spec_path = os.path.join(PROJECT_DIR, "RealtimeGameTranslator.spec")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_path]
    step(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {result.returncode}")
    step("PyInstaller compilation completed successfully!")

def copy_user_configs():
    step("Copying editable config files to release folder...")
    for filename in ["config.json", "glossary.json", "app_icon.ico"]:
        src = os.path.join(PROJECT_DIR, filename)
        dst = os.path.join(APP_OUT_DIR, filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            step(f"Copied {filename} -> {dst}")

    # Create README_USAGE.txt
    readme_content = """===============================================================
  Realtime Game Translator - Audio Transcription & Translation
===============================================================

วิธีการใช้งาน (How to Use):
1. ดับเบิลคลิกที่ "RealtimeGameTranslator.exe" เพื่อเปิดโปรแกรม
   (โหมดนี้จะเปิดเฉพาะหน้าต่างแปลภาษาโปร่งใส ไม่มีหน้าต่างจอดำ)
   
2. หากต้องการดู Log หรือเช็คการทำงาน/ข้อผิดพลาด สามารถเปิด "RealtimeGameTranslator_Debug.exe"

3. การตั้งค่า (Configuration):
   - สามารถเปิดแก้ไขไฟล์ 'config.json' เพื่อตั้งค่า:
     * gemini_api_key (หากต้องการใช้โมเดลแปลภาษา Google Gemini)
     * engine (เช่น 'google' สำหรับการแปลฟรีความเร็วสูง ~0.2s, หรือ 'gemini')
     * ภาษาต้นทางและปลายทาง (source_lang / target_lang)
     * ขนาดตัวอักษร, สี, และความโปร่งแสงของกรอบ Overlay
   
   - สามารถเปิดแก้ไขไฟล์ 'glossary.json' เพื่อเพิ่มคำศัพท์เฉพาะของเกม เช่น:
     "HP": "พลังชีวิต", "Mana": "มานา"

4. การใช้งานกับเสียงเกม / YouTube:
   - โปรแกรมจะดักจับเสียงจากระบบคอมพิวเตอร์ (System Audio Loopback) อัตโนมัติ
   - เมื่อเปิดเกมหรือวิดีโอ ข้อความต้นฉบับและคำแปลภาษาไทยจะแสดงบนหน้าจอทันที!

===============================================================
"""
    with open(os.path.join(APP_OUT_DIR, "README_USAGE.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    step("Created README_USAGE.txt")

def create_portable_zip():
    log("Creating Portable Distribution ZIP...")
    zip_path = os.path.join(DIST_DIR, "RealtimeGameTranslator_v1.0_Portable.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)

    step(f"Compressing {APP_OUT_DIR} -> {zip_path}...")
    start_time = time.time()
    file_count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        for root, dirs, files in os.walk(APP_OUT_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, DIST_DIR)
                zipf.write(full_path, rel_path)
                file_count += 1
    
    elapsed = time.time() - start_time
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    step(f"ZIP created: {zip_path} ({zip_size_mb:.1f} MB, {file_count} files, {elapsed:.1f}s)")

def generate_inno_setup_script():
    step("Generating Inno Setup script (installer.iss)...")
    iss_content = f"""#define MyAppName "Realtime Game Translator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Realtime Translator Team"
#define MyAppExeName "RealtimeGameTranslator.exe"
#define MyAppDebugExeName "RealtimeGameTranslator_Debug.exe"
#define MyAppIcon "{os.path.join(PROJECT_DIR, 'app_icon.ico')}"
#define SourceDir "{APP_OUT_DIR}"

[Setup]
AppId={{{{E8A42D77-3B21-4F1A-B82C-1E43D8F5C9A1}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir="{DIST_DIR}"
OutputBaseFilename=RealtimeGameTranslator_Setup
SetupIconFile={{#MyAppIcon}}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"

[Files]
Source: "{{#SourceDir}}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\app_icon.ico"
Name: "{{autoprograms}}\\{{#MyAppName}} (Debug Console)"; Filename: "{{app}}\\{{#MyAppDebugExeName}}"; IconFilename: "{{app}}\\app_icon.ico"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
"""
    iss_path = os.path.join(PROJECT_DIR, "installer.iss")
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(iss_content)
    step(f"Inno Setup script saved to: {iss_path}")

    # Check if Inno Setup compiler is installed
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for ip in inno_paths:
        if os.path.exists(ip):
            step(f"Inno Setup Compiler detected at {ip}! Building installer...")
            try:
                subprocess.run([ip, iss_path], check=True)
                step(f"Installer created: {os.path.join(DIST_DIR, 'RealtimeGameTranslator_Setup.exe')}")
            except Exception as e:
                step(f"Notice: Failed to run ISCC.exe: {e}")
            break

def main():
    total_start = time.time()
    clean_previous_build()
    ensure_icon()
    run_pyinstaller()
    copy_user_configs()
    generate_inno_setup_script()
    create_portable_zip()
    total_elapsed = time.time() - total_start
    log(f"All Build Steps Complete in {total_elapsed:.1f}s!")
    print(f"\n[+] Executable Output: {os.path.join(APP_OUT_DIR, 'RealtimeGameTranslator.exe')}")
    print(f"[+] Portable ZIP Archive: {os.path.join(DIST_DIR, 'RealtimeGameTranslator_v1.0_Portable.zip')}")
    print(f"[+] Inno Setup Script: {os.path.join(PROJECT_DIR, 'installer.iss')}")

if __name__ == "__main__":
    main()
