# 🎮 Real-Time Game & Media Translator (EN / Any ➔ TH)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://microsoft.com/windows)
[![GUI](https://img.shields.io/badge/GUI-PyQt6%20%7C%20Tkinter-41CD52.svg)](https://riverbankcomputing.com/software/pyqt/)
[![AI](https://img.shields.io/badge/AI-faster--whisper%20%7C%20Gemini%20%7C%20Ollama-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

โปรแกรมแปลภาษาเกมและสื่อวิดีโอแบบเรียลไทม์ (**Real-Time Translator**) จากภาษาอังกฤษและภาษาอื่น ๆ เป็นภาษาไทย รองรับทั้งการ**จับภาพหน้าจอ (Screen OCR)** และการ**ดักฟังเสียงเกม/YouTube โดยตรงจากระบบเสียงในเครื่อง (WASAPI Loopback Audio Speech-to-Text)** พร้อมระบบแสดงผล **Transparent Subtitle Overlay** ลอยทับหน้าจอเกม เล่นเกมได้ต่อเนื่องไม่สะดุด ไม่ต้องคอยกดสลับหน้าต่าง

---

## ✨ Features (คุณสมบัติเด่น)

### 1. 📺 ระบบจับภาพหน้าจอ (Screen OCR Translation)
- 🎯 **3 โหมดการจับภาพ**:
  - **ROI Mode (Region of Interest)**: ลากเลือกเฉพาะกล่องข้อความหรือซับไตเติลเกมได้อย่างอิสระ
  - **Bottom Subtitle Preset**: คลิกเดียวเซ็ตพื้นที่จับภาพ 25% ด้านล่างจอสำหรับเกมหรือภาพยนตร์
  - **Fullscreen Mode**: ตรวจจับและแปลข้อความทั่วทั้งหน้าจอ
- ⚡ **Dual OCR Engines**:
  - **Windows Native OCR (`winocr`)**: ใช้งาน API ความเร็วสูงที่ติดมากับ Windows 10/11 กินสเปกต่ำ ไม่ต้องติดตั้งไฟล์โมเดลเพิ่ม
  - **Tesseract OCR**: รองรับการปรับแต่ง Contrast Enhancement, Binarization และ Image Upscaling เพื่อความแม่นยำสูงสุด
- 🛡️ **Smart Text Debounce**: ตรวจจับความเปลี่ยนแปลงของข้อความอัตโนมัติ ไม่สั่งแปลซ้ำหากข้อความเดิมยังไม่เปลี่ยน ช่วยประหยัดเน็ตและลดอาการกระตุก

### 2. 🔊 ระบบแปลจากเสียงในเกมโดยตรง (Internal Audio STT Translation)
- 🎧 **WASAPI Loopback Capture**: ดักจับเสียงเกม, คัตซีน, YouTube, Discord หรือวิดีโอสตรีมมิ่งจากภายในการ์ดเสียงของ Windows โดยตรง ไม่ต้องต่อสายแยก และไม่ต้องเปิด Stereo Mix
- 🎙️ **Microphone Support**: สลับไปรับเสียงจากไมโครโฟนได้สำหรับฟังบทสนทนาสด
- 🤖 **Offline AI STT (faster-whisper)**: ถอดความเสียงพูดด้วยโมเดล Whisper (CTranslate2) รองรับตั้งแต่ `tiny`, `base`, `small`, `medium` จนถึง `large-v3` บน CPU หรือ GPU (NVIDIA CUDA)
- ⚡ **Gemini Direct Audio Mode**: ส่งสัญญาณเสียงเข้าประมวลผลกับ Google Gemini Multimodal แปลงเสียงเป็นซับไทยได้ในรอบเดียวอย่างรวดเร็ว

### 3. 🌐 เครื่องมือแปลภาษาอัจฉริยะ (Multi-Engine Translation)
- 🧠 **Google Gemini AI (Gemini 2.5 / 3.6 Flash)**: แปลสำนวนเกมได้สละสลวย เข้ากับบริบทบทสนทนา ไม่แข็งทื่อเหมือนเครื่องแปลทั่วไป
- 🦙 **Ollama Local LLM**: รองรับการเชื่อมต่อกับโมเดลภาษาแบบ Local (เช่น `gemma2:2b`, `qwen2.5:3b`) เพื่อแปลแบบออฟไลน์ 100% ปลอดภัยและฟรี
- 🔄 **Auto-Failover System**: มีระบบสลับไปใช้ **Google Translate** (`deep-translator` / `translatepy`) อัตโนมัติเมื่อบริการหลักเกิดข้อผิดพลาดหรือโควตาหมด

### 4. 🪟 หน้าต่างซับไตเติลโปร่งแสง (Transparent Overlay)
- 🖱️ **Click-Through / Mouse-Transparent**: ป้องกันการคลิกเมาส์โดนหน้าต่างซับไตเติลขณะเล่นเกม (เปิด/ปิดด้วยปุ่มลัด `F10`)
- 🎨 **Fully Customizable**: ปรับขนาดฟอนต์, สีตัวอักษร, สีพื้นหลัง, ระดับความโปร่งใส (Opacity) และเลือกเปิด/ปิดการแสดงภาษาต้นฉบับได้
- 📐 **Glowing ROI Border**: กรอบไฟนีออนแสดงขอบเขตพื้นที่ที่กำลังอ่านตัวอักษรบนหน้าจอ

### 5. ⌨️ คีย์ลัดควบคุมระดับสากล (Global Hotkeys)
สั่งการได้ทันทีแม้เกมกำลังทำงานแบบเต็มหน้าจอ (Fullscreen):
| คีย์ลัด | ฟังก์ชัน | คำอธิบาย |
|:---:|:---|:---|
| **`F7`** | **Snapshot Translate** | บังคับแคปเจอร์และแปลทันที 1 ครั้ง |
| **`F8`** | **Toggle Pause/Resume** | หยุดชั่วคราว หรือเริ่มทำงานระบบแปลอัตโนมัติ |
| **`F9`** | **Select New ROI** | ลากเมาส์เลือกพื้นที่บนหน้าจอใหม่อย่างรวดเร็ว |
| **`F10`** | **Lock / Unlock Overlay** | สลับโหมดล็อกหน้าต่างซับให้คลิกทะลุเมาส์ (Click-through) |

---

## 🏗️ Architecture (สถาปัตยกรรมระบบ)

```text
       ┌───────────────────────────────┐        ┌───────────────────────────────┐
       │   Game Screen Display (MSS)   │        │   PC Internal Audio (WASAPI)  │
       └──────────────┬────────────────┘        └──────────────┬────────────────┘
                      │                                        │
                      ▼                                        ▼
       ┌───────────────────────────────┐        ┌───────────────────────────────┐
       │  Image Preprocessing (OpenCV) │        │  Audio Buffer & VAD Filtering │
       └──────────────┬────────────────┘        └──────────────┬────────────────┘
                      │                                        │
                      ▼                                        ▼
       ┌───────────────────────────────┐        ┌───────────────────────────────┐
       │  OCR Engine (WinOCR / Tess)   │        │  STT Engine (faster-whisper)  │
       └──────────────┬────────────────┘        └──────────────┬────────────────┘
                      │ (Detected Text)                        │ (Spoken Text)
                      └────────────────┬───────────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │    Text Pipeline & Diff Cache   │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │    Smart Translation Services   │
                      │  [Gemini AI / Ollama / Google]  │
                      └────────────────┬────────────────┘
                                       │ (Thai Subtitles)
                                       ▼
                      ┌─────────────────────────────────┐
                      │  PyQt6 / Tkinter Floating HUD   │
                      │   (Click-through Subtitles)     │
                      └─────────────────────────────────┘
```

---

## 📦 โครงสร้างโฟลเดอร์โปรเจกต์ (Project Structure)

```text
realtime-game-translator/
├── src/                               # โมดูลหลักสำหรับ PyQt6 Desktop App
│   ├── audio_listener.py              # ถอดความและแปลเสียงระบบ (WASAPI Loopback & Gemini)
│   ├── capture.py                     # ระบบจับภาพหน้าจอด้วย mss ความเร็วสูง
│   ├── controller.py                  # Background Worker ควบคุมวงรอบ OCR & Translation
│   ├── ocr.py                         # OCR Engine (Windows Native OCR & Tesseract)
│   ├── overlay.py                     # หน้าต่างซับไตเติลโปร่งแสง & ROI Selector
│   ├── translator.py                  # ระบบแปลภาษาหลัก (Gemini, Google Translate, Cache)
│   ├── ui_panel.py                    # แผงตั้งค่าและแผงควบคุมหลัก (Modern Dark UI)
│   └── utils.py                       # Image processing, ConfigManager, Text cleaning
├── live_translation/                  # โมดูลเสริมสำหรับ Live Audio Whisper Pipeline
│   ├── sessions.py                    # จัดการเซสชันการถอดเสียงและข้อความ
│   ├── text_pipeline.py               # จัดการข้อความซ้ำ, เติมเครื่องหมาย, ตัดคำหลอน
│   └── translators.py                 # Multi-backend translators (Gemini, Ollama, Fallback)
├── config.json                        # ไฟล์คอนฟิกหลักของระบบ (ปรับแต่งหรือเซฟผ่าน GUI)
├── live_translate_windows.py          # แอปสตรีมมิ่งถอดเสียงและแปลแบบสด (Standalone CLI/HUD)
├── main.py                            # จุดเริ่มต้นหลักของโปรแกรม (Full GUI Control Panel)
├── requirements.txt                   # รายการไลบรารี Python ทั้งหมด
└── run_windows.bat                    # สคริปต์คลิกเดียวเพื่อสร้าง venv, ติดตั้ง และรันโปรแกรม
```

---

## 🚀 วิธีการติดตั้งและการเริ่มใช้งาน (Getting Started)

### ความต้องการของระบบ (System Requirements)
- **ระบบปฏิบัติการ**: Windows 10 หรือ Windows 11 (64-bit)
- **Python**: เวอร์ชัน 3.10 ขึ้นไป (แนะนำ Python 3.11 หรือ 3.12)
- **GPU (ทางเลือก)**: NVIDIA GPU พร้อมติดตั้ง CUDA Toolkit (หากต้องการใช้งาน faster-whisper ด้วยการประมวลผลผ่าน GPU)

---

### ขั้นตอนที่ 1: ดาวน์โหลดโปรเจกต์ (Clone Repository)
```bash
git clone https://github.com/<YOUR_USERNAME>/realtime-game-translator.git
cd realtime-game-translator
```

### ขั้นตอนที่ 2: สร้างและเปิดใช้งาน Virtual Environment
```bash
python -m venv .venv
# เปิดใช้งานบน Windows PowerShell / Command Prompt
.venv\Scripts\activate
```

### ขั้นตอนที่ 3: ติดตั้งไลบรารีที่จำเป็น (Install Dependencies)
```bash
pip install -r requirements.txt
```

> [!TIP]
> **สำหรับการเปิดใช้งาน GPU Acceleration บน NVIDIA:**
> หากต้องการให้ `faster-whisper` ถอดเสียงได้รวดเร็วขึ้นผ่านการ์ดจอ ให้ติดตั้ง PyTorch + CUDA:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu121
> ```

---

## 🎮 วิธีการเรียกใช้งาน (How to Run)

โปรแกรมมีรูปแบบการใช้งานหลักให้เลือก 2 รูปแบบตามความต้องการ:

### วิธีที่ 1: ใช้งานผ่าน Full GUI App (แนะนำสำหรับการเล่นเกม)
เป็นหน้าจอควบคุมครบวงจร ปรับแต่งได้ทั้งหน้าจอจับภาพ, ระบบเสียง, การแปล และตั้งค่าสีซับไตเติลผ่าน GUI:

```bash
python main.py
```

#### การใช้งานในแอปหลัก:
1. **เลือกโหมดการจับภาพ (Capture Mode)**:
   - `🎯 จับภาพ ROI`: ลากคลุมพื้นที่ตัวหนังสือเกม (กด `F9` เพื่อเลือกใหม่)
   - `🖥️ ทั้งหน้าจอ`: สำหรับเกมที่ตัวหนังสือกระจายทั่วจอ
   - `🔊 ฟังเสียงอย่างเดียว`: ปิดการแคปจอ และดักฟังเสียงเกม/YouTube โดยตรง
2. **ตั้งค่า API Key**:
   - ไปที่แท็บ **⚙️ ระบบแปล & เสียง & OCR** ใส่ **Google Gemini API Key** เพื่อความลื่นไหลและสำนวนแปลที่ยอดเยี่ยม (หากไม่มี คีย์บอร์ดจะสลับไปใช้ Google Translate ฟรีอัตโนมัติ)
3. **ปรับแต่งและล็อกหน้าต่างซับ**:
   - ย้ายหน้าต่างซับไปยังจุดที่ต้องการ
   - กดปุ่ม **`F10`** เพื่อเปิดโหมด **Click-Through (ล็อกหน้าต่าง)** เมาส์จะทะลุหน้าต่างซับ ทำให้ควบคุมเกมได้ตามปกติ

---

### วิธีที่ 2: รันผ่าน Windows Batch File (คลิกเดียวรันได้เลย)
สามารถดับเบิลคลิกไฟล์ **`run_windows.bat`** เพื่อเริ่มโปรแกรมได้ทันที (สคริปต์จะตรวจสอบและสร้าง `.venv` รวมถึงติดตั้งไลบรารีให้อัตโนมัติในครั้งแรก)

---

### วิธีที่ 3: ใช้งาน Standalone Live Audio Stream Translator
เหมาะสำหรับสตรีมเมอร์ หรือผู้ที่ต้องการฟังเสียงภาษาอังกฤษ/ญี่ปุ่นจาก YouTube, สตรีม หรือเกม แล้วแปลขึ้นแถบซับลอยแบบสด ๆ ด้วย `faster-whisper`:

```bash
# ตรวจสอบหมายเลข Audio Device ในเครื่อง
python live_translate_windows.py --list

# รันโหมดดักฟังเสียงระบบ (WASAPI Loopback) แปลด้วย Gemini
python live_translate_windows.py --mode loopback --whisper base --target th

# รันร่วมกับ Local LLM (Ollama)
python live_translate_windows.py --mode loopback --ollama-model gemma2:2b --target th

# รันโหมดไมโครโฟน
python live_translate_windows.py --mode mic --whisper small --target th
```

#### ตัวเลือก CLI ที่สำคัญ:
- `--mode`: เลือกแหล่งเสียง `loopback` (เสียงในคอม) หรือ `mic` (ไมโครโฟน)
- `--whisper`: เลือกขนาดโมเดล (`tiny`, `base`, `small`, `medium`, `turbo`, `large-v3`)
- `--device-type`: ประมวลผลผ่าน `cpu` หรือ `cuda`
- `--gemini-key`: ใส่ Gemini API Key หรือจะระบุไว้ใน `config.json` ก็ได้
- `--no-window`: แสดงผลคำแปลเฉพาะบน Console (ไม่เปิดหน้าต่าง Overlay)

---

## ⚙️ โครงสร้างไฟล์การตั้งค่า (`config.json`)

สามารถตั้งค่าล่วงหน้าผ่านไฟล์ [config.json](file:///C:/Users/ASUS/realtime-game-translator/config.json) ได้โดยตรง:

```json
{
    "roi": {
        "left": 28,
        "top": 180,
        "width": 1028,
        "height": 601
    },
    "overlay": {
        "x": 236,
        "y": 703,
        "width": 1040,
        "height": 113,
        "font_size": 22,
        "font_color": "#FFFFFF",
        "bg_color": "#000000",
        "bg_opacity": 0.35,
        "show_original": false,
        "click_through": false,
        "show_roi_border": false
    },
    "translation": {
        "engine": "google",
        "source_lang": "en",
        "target_lang": "th",
        "gemini_api_key": "YOUR_GEMINI_API_KEY",
        "gemini_model": "gemini-3.6-flash"
    },
    "ocr": {
        "engine": "winocr",
        "lang": "en",
        "upscale_factor": 1.5,
        "contrast_enhance": true,
        "binarize": true
    },
    "app": {
        "preset": "game",
        "interval_ms": 500,
        "similarity_threshold": 0.85,
        "hotkeys": {
            "snapshot_translate": "f7",
            "toggle_translation": "f8",
            "select_roi": "f9",
            "toggle_lock": "f10"
        },
        "is_fullscreen": false,
        "capture_mode": "roi"
    },
    "audio": {
        "enabled": true,
        "mode": "loopback"
    }
}
```

---

## ❓ คำถามที่พบบ่อย & การแก้ไขปัญหา (Troubleshooting & FAQ)

<details>
<summary><b>1. กดปุ่มลัด (Hotkeys F7 - F10) ในเกมไม่ได้ผล ทำอย่างไร?</b></summary>

เกมหลายเกมรันด้วยสิทธิ์ Administrator ทำให้โปรแกรมภายนอกดักจับคีย์ลัดไม่ได้
- **วิธีแก้**: ให้เปิด Command Prompt / PowerShell ด้วยสิทธิ์ **Run as Administrator** แล้วค่อยรัน `python main.py`
</details>

<details>
<summary><b>2. ใช้งานโหมดเสียง Loopback แล้วไม่มีเสียงขึ้นในโปรแกรม?</b></summary>

- ตรวจสอบว่าเปิดเสียงเกมหรือ YouTube อยู่หรือไม่ (เสียงต้องมีระดับความดังเกินเกณฑ์ Silence RMS)
- ตรวจสอบว่า Default Playback Device ของ Windows คือลำโพงหรือหูฟังที่คุณกำลังใช้งาน
- สามารถตรวจสอบลำดับอุปกรณ์เสียงได้ด้วยคำสั่ง:
  ```bash
  python live_translate_windows.py --list
  ```
</details>

<details>
<summary><b>3. ขอรับ Google Gemini API Key ได้จากที่ไหน?</b></summary>

- สามารถขอรับ API Key ฟรีได้จาก [Google AI Studio](https://aistudio.google.com/)
- นำ API Key ที่ได้มากรอกในช่องตั้งค่าของ Control Panel หรือบันทึกลงใน `config.json`
</details>

<details>
<summary><b>4. ตัวหนังสือบนหน้าจออ่านไม่ติด หรือคำแปลเพี้ยน?</b></summary>

- ลองกด `F9` แล้วลากคลุมเฉพาะบริเวณตัวหนังสือ ไม่ให้ติดพื้นหลังของเกมที่เคลื่อนไหวมากเกินไป
- หากฟอนต์เกมมีลวดลายซับซ้อน ให้เปิดใช้งาน `Binarize` (ปรับขาวดำ) หรือปรับระดับ `Upscale Factor` ในหน้าต่างการตั้งค่า
- สำหรับ Windows Native OCR ให้ตรวจสอบว่ามี Language Pack ภาษาอังกฤษติดตั้งอยู่ใน Windows (Settings -> Time & Language -> Language & Region)
</details>

---

## 🗺️ แผนการพัฒนาในอนาคต (Roadmap)

- [x] ระบบจับภาพความเร็วสูงด้วย `mss` และการลากเลือก ROI แบบ Interactive
- [x] รองรับ Windows Native OCR (`winocr`) ความเร็วสูง
- [x] ระบบดักฟังเสียงเกมในเครื่อง WASAPI Loopback Audio Capture
- [x] รองรับการแปลงเสียงเป็นข้อความด้วย AI ออฟไลน์ `faster-whisper`
- [x] รองรับการแปลด้วย Google Translate, Gemini AI และ Ollama Local LLM
- [x] หน้าต่างซับไตเติลโปร่งแสงแบบ Click-Through ไม่กวนการเล่นเกม
- [x] คีย์ลัดระดับสากล (Global Hotkeys)
- [ ] ระบบสร้างตัวติดตั้ง Standalone Executable (.exe) ผ่าน PyInstaller
- [ ] ระบบจัดการคำศัพท์เฉพาะทางในเกม (Gaming Glossary / Custom Dictionary)

---

## 📄 ใบอนุญาต (License)

โปรเจกต์นี้เผยแพร่ภายใต้สัญญาอนุญาต [MIT License](LICENSE) สามารถนำไปพัฒนาต่อยอด ใช้งาน และแจกจ่ายได้อย่างอิสระ
