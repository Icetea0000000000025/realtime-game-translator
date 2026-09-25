# Real-Time Game & Media Audio Translator (EN / Multi-Language ➔ TH)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://microsoft.com/windows)
[![GUI](https://img.shields.io/badge/GUI-Tkinter-41CD52.svg)](https://docs.python.org/3/library/tkinter.html)
[![STT Engine](https://img.shields.io/badge/STT-Faster--Whisper%20%7C%20CUDA-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Translation](https://img.shields.io/badge/Translation-Google%20Fast%20%7C%20Gemini%20AI-9cf.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

ระบบถอดเสียงพูดและแปลภาษาแบบเรียลไทม์ (**Real-Time Audio Speech-to-Text & Translation**) สำหรับระบบปฏิบัติการ Windows ออกแบบมาสำหรับการเล่นเกม ดูวิดีโอสตรีมมิ่ง คัตซีน หรือการรับชมสื่อต่างประเทศ โดยดักจับสัญญาณเสียงภายในเครื่องโดยตรงผ่าน **WASAPI Loopback** แปลงเสียงเป็นข้อความด้วยแบบจำลองปัญญาประดิษฐ์ **Faster-Whisper** ที่รองรับการประมวลผลความเร็วสูงบนการ์ดจอ NVIDIA RTX (CUDA) และแปลเป็นภาษาไทยผ่านเอนจินความหน่วงต่ำ พร้อมหน้าต่างซับไตเติลโปร่งแสง (**Transparent Overlay**) ลอยทับหน้าจอเกมโดยไม่บดบังหรือรบกวนการเล่น

---

## คุณสมบัติการทำงานหลัก (Core Features)

### 1. ระบบดักจับสัญญาณเสียงความเร็วสูง (Low-Latency Audio Capture)
- **WASAPI Loopback Capture:** ดักจับเสียงเกม คัตซีน และเสียงระบบจาก Windows โดยตรง ไม่ต้องต่อสายสัญญาณภายนอก และไม่ต้องเปิดใช้งาน Stereo Mix
- **Microphone Input Support:** สลับรับสัญญาณเสียงจากไมโครโฟนสำหรับการสนทนาสดได้
- **Dynamic Silence Cut & Buffering:** ตัดช่วงเสียงเงียบอัตโนมัติ (Silence Threshold RMS) และส่งบล็อกเสียงเข้าประมวลผลขนาด 0.2 วินาที เพื่อลดความหน่วงสะสม

### 2. ระบบถอดรหัสเสียงออฟไลน์ (Offline Speech-to-Text Engine)
- **Faster-Whisper (CTranslate2):** ถอดความเสียงพูดเป็นข้อความ รองรับโมเดลตั้งแต่ขนาด `tiny`, `base`, `small`, `medium`, `turbo` จนถึง `large-v3`
- **NVIDIA GPU Acceleration (CUDA 12 & cuDNN):** ระบบลงทะเบียนและโหลดไดนามิกลิงก์ไลบรารี (DLL) ของ CUDA/cuDNN อัตโนมัติ รองรับการประมวลผลบนการ์ดจอ NVIDIA RTX (เช่น RTX 2050, 3060, 4060) ให้ความเร็วในการประมวลผลคำพูดในระดับ 150 - 250 มิลลิวินาที
- **Voice Text Normalization:** กรองคำซ้ำ (Deduplication) และตัดสัญญาณเสียงผิดเพี้ยนหรือคำหลอน (Hallucination Filtering)

### 3. ระบบแปลภาษาหลายรูปแบบ (Multi-Engine Translation)
- **Google Fast Engine (ค่าเริ่มต้น):** ประมวลผลแปลข้อความด้วยความเร็วสูงพิเศษ (Latency ~0.2 วินาที) ไม่ต้องใช้ API Key เหมาะสำหรับการเล่นเกมที่ต้องการคำแปลทันที
- **Google Gemini AI:** แปลโดยวิเคราะห์บริบทของบทสนทนาและสำนวนเกม รองรับพจนานุกรมคำศัพท์เฉพาะทาง (`glossary.json`)
- **Dynamic Hotkey Switch:** สลับเอนจินแปลภาษาได้ทันทีขณะใช้งานผ่านปุ่มลัด `F8`
- **Multi-Language Support:** รองรับเสียงต้นทางภาษาอังกฤษ (EN), ญี่ปุ่น (JA), เกาหลี (KO), จีน (ZH) หรือตรวจจับภาษาอัตโนมัติ (Auto Detect) และแปลเป็นภาษาไทย (TH), อังกฤษ (EN) หรือญี่ปุ่น (JA)

### 4. หน้าต่างแสดงผลซับไตเติลแบบโปร่งแสง (Dual-Mode Overlay Interface)
- **Compact HUD Mode (โหมดย่อ):** หน้าต่างซับไตเติลโปร่งแสง 100% ไร้กรอบทึบรบกวนสายตา แสดงตัวอักษรพร้อมระบบเงา 8 ทิศทาง (8-Direction Drop Shadow) อ่านง่ายในทุกฉากของเกม
- **Full Dashboard Mode (โหมดหน้าใหญ่):** แผงควบคุม 2 คอลัมน์ แสดงข้อความเสียงต้นฉบับและข้อความคำแปล พร้อมสถานะระบบ
- **Click-Through Lock:** โหมดล็อกหน้าต่างทำให้การคลิกเมาส์ทะลุผ่านไปยังหน้าจอเกมได้ 100%
- **Quick Context Menu:** เมนูคลิกขวาสำหรับปรับแต่งขนาดฟอนต์ สีตัวอักษร การเลือกภาษา และการตั้งค่าแถบควบคุม

---

## สถาปัตยกรรมระบบ (System Architecture)

```text
 ┌───────────────────────────────┐        ┌───────────────────────────────┐
 │   PC Internal Audio (WASAPI)  │        │   Microphone Audio (Direct)   │
 └──────────────┬────────────────┘        └──────────────┬────────────────┘
                │                                        │
                └────────────────┬───────────────────────┘
                                 │
                                 ▼
                ┌─────────────────────────────────┐
                │ Audio Ring Buffer & Silence Cut │
                │   (0.2s chunks, RMS detection)  │
                └────────────────┬────────────────┘
                                 │
                                 ▼
                ┌─────────────────────────────────┐
                │   Faster-Whisper STT Engine     │
                │  [NVIDIA CUDA 12 GPU / CPU]     │
                └────────────────┬────────────────┘
                                 │ (Spoken Text)
                                 ▼
                ┌─────────────────────────────────┐
                │ Text Pipeline & Hallucination   │
                │  Filter / Gaming Glossary Cache │
                └────────────────┬────────────────┘
                                 │
                                 ▼
                ┌─────────────────────────────────┐
                │   Translation Engine Dispatcher │
                │ ⚡ Fast Engine  |  🤖 Gemini AI  │
                └────────────────┬────────────────┘
                                 │ (Translated Subtitles)
                                 ▼
                ┌─────────────────────────────────┐
                │  Tkinter Transparent HUD Window │
                │  (Click-through / 8-Way Outline)│
                └─────────────────────────────────┘
```

---

## โครงสร้างโฟลเดอร์โปรเจกต์ (Project Structure)

```text
realtime-game-translator/
├── live_translation/                  # โมดูลประมวลผลข้อความและระบบแปลภาษา
│   ├── sessions.py                    # จัดการเซสชันการถอดเสียงและข้อความ
│   ├── text_pipeline.py               # ตัวกรองคำซ้ำ เติมเครื่องหมาย และตัดคำหลอน
│   └── translators.py                 # ตัวจัดการเอนจินแปลภาษา (Fast Google, Gemini, Ollama)
├── .env                               # เก็บ API Key ส่วนตัว (ไม่ถูกนำขึ้น Git)
├── config.json                        # การตั้งค่าพารามิเตอร์เริ่มต้นของระบบ
├── glossary.json                      # ฐานข้อมูลคำศัพท์เฉพาะและชื่อตัวละครในเกม
├── live_translate_windows.py          # โปรแกรมหลัก: ระบบดักจับเสียง ถอดความ แปล และแสดงผล Overlay
├── main.py                            # จุดเริ่มต้นสำหรับรันแอปพลิเคชัน
├── requirements.txt                   # รายการไลบรารีที่โปรเจกต์ต้องการ
└── run_windows.bat                    # สคริปต์แบตช์สำหรับเริ่มโปรแกรมด้วยการคลิกเดียว
```

---

## ปุ่มลัดและการควบคุม (Controls & Hotkeys)

| ปุ่มลัด | ฟังก์ชัน | รายละเอียดการทำงาน |
|:---:|:---|:---|
| **`F2`** | **Toggle Window Mode** | สลับระหว่างโหมดซับโปร่งใส (Compact HUD) และแดชบอร์ดเต็ม 2 คอลัมน์ (Full Mode) |
| **`F3`** | **Toggle Control Bar** | สลับการซ่อนหรือแสดงแถบเครื่องมือด้านบนในโหมด Compact HUD ทันที |
| **`F4` / `F10`** | **Toggle Lock / Click-Through** | สลับสถานะล็อกตำแหน่งหน้าต่างซับไตเติล และเปิดโหมดเมาส์คลิกทะลุเข้าเกม |
| **`F8`** | **Toggle Translation Engine** | สลับระหว่าง **Google Fast** (เร็ว ~0.2s) และ **Gemini AI** (วิเคราะห์บริบท) |
| **คลิกขวาที่แถบซับ** | **Context Menu** | เปิดเมนูตั้งค่าด่วน: ภาษาต้นทาง, ภาษาปลายทาง, สีและขนาดตัวอักษร, พฤติกรรมแถบควบคุม |

---

## การติดตั้งและการเริ่มใช้งาน (Installation & Setup)

### ความต้องการของระบบ (System Requirements)
- **ระบบปฏิบัติการ:** Windows 10 หรือ Windows 11 (64-bit)
- **Python:** เวอร์ชัน 3.10 ขึ้นไป (แนะนำ Python 3.11 หรือ 3.12)
- **ฮาร์ดแวร์ประมวลผล (ทางเลือกเพื่อประสิทธิภาพสูงสุด):** การ์ดจอ NVIDIA ซีรีส์ GTX / RTX ที่รองรับสถาปัตยกรรม CUDA 12

---

### ขั้นตอนที่ 1: ดาวน์โหลดโปรเจกต์
```bash
git clone https://github.com/Icetea0000000000025/realtime-game-translator.git
cd realtime-game-translator
```

### ขั้นตอนที่ 2: สร้างและเปิดใช้งานสภาพแวดล้อมเสมือน (Virtual Environment)
```bash
python -m venv .venv
.venv\Scripts\activate
```

### ขั้นตอนที่ 3: ติดตั้งไลบรารีที่จำเป็น
```bash
pip install -r requirements.txt
```

> [!NOTE]
> ในไฟล์ `requirements.txt` มีแพ็กเกจ `nvidia-cublas-cu12` และ `nvidia-cudnn-cu12` รวมอยู่แล้ว เมื่อติดตั้งเสร็จสิ้น ตัวโปรแกรมจะตรวจจับและดึงไฟล์ DLL ของ CUDA มาประมวลผลบนการ์ดจอ NVIDIA RTX อัตโนมัติ

### ขั้นตอนที่ 4: ตั้งค่า Google Gemini API Key (ทางเลือก)
หากต้องการใช้งานเอนจิน Google Gemini AI ร่วมด้วย:
1. สร้างไฟล์ชื่อ `.env` ในโฟลเดอร์หลักของโปรเจกต์
2. ระบุ API Key ลงในไฟล์:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(หากไม่ระบุคีย์ ระบบจะใช้งานเอนจิน Google Fast ความเร็วสูงเป็นค่าเริ่มต้นโดยอัตโนมัติ)*

---

## วิธีการเรียกใช้งาน (How to Run)

### วิธีที่ 1: เรียกใช้งานแบบเร็วผ่านคำสั่งหลัก
```bash
python main.py
```
หรือดับเบิลคลิกที่ไฟล์ **`run_windows.bat`** เพื่อเปิดโปรแกรมทันที

### วิธีที่ 2: ปรับแต่งผ่าน Command Line Interface (CLI)
สามารถกำหนดค่าพารามิเตอร์การทำงานขั้นสูงผ่าน `live_translate_windows.py` ได้:

```bash
# ตรวจสอบรายการอุปกรณ์เสียงทั้งหมดในระบบ
python live_translate_windows.py --list

# กำหนดขนาดโมเดล Whisper และอุปกรณ์ประมวลผล
python live_translate_windows.py --whisper base --device-type cuda --compute-type float16

# ใช้งานโหมดรับสัญญาณเสียงจากไมโครโฟน
python live_translate_windows.py --mode mic --target th

# รันโดยแสดงผลเฉพาะในคอนโซล (ไม่เปิดหน้าต่าง Overlay)
python live_translate_windows.py --no-window
```

#### พารามิเตอร์ CLI ที่สำคัญ:
- `--mode`: เลือกแหล่งสัญญาณเสียง `loopback` (เสียงในคอม) หรือ `mic` (ไมโครโฟน)
- `--whisper`: เลือกขนาดของโมเดล Faster-Whisper (`tiny`, `base`, `small`, `medium`, `turbo`, `large-v3`)
- `--device-type`: หน่วยประมวลผล `cuda` (การ์ดจอ NVIDIA) หรือ `cpu`
- `--compute-type`: รูปแบบความละเอียดการคำนวณ (`float16`, `int8`, `float32`)
- `--source`: ภาษาของเสียงพูดต้นฉบับ (เช่น `en`, `ja`, `ko`, `zh`, `auto`)
- `--target`: ภาษาคำแปลที่ต้องการ (เช่น `th`, `en`, `ja`)

---

## รูปแบบไฟล์การตั้งค่า (Configuration)

### [config.json](file:///C:/Users/ASUS/realtime-game-translator/config.json)
```json
{
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
        "auto_hide_seconds": 6
    },
    "translation": {
        "engine": "google",
        "source_lang": "en",
        "target_lang": "th",
        "gemini_api_key": "",
        "gemini_model": "gemini-3.5-flash-lite"
    },
    "app": {
        "preset": "game",
        "interval_ms": 500,
        "similarity_threshold": 0.85
    },
    "audio": {
        "enabled": true,
        "mode": "loopback"
    }
}
```

---

## แผนการพัฒนาระบบ (Development Roadmap)

เอกสารฉบับนี้กำหนดกรอบการพัฒนาระบบแปลเสียงเรียลไทม์สำหรับเกมและสื่อมัลติมีเดีย โดยแบ่งออกเป็น 3 ระยะตามลำดับความคุ้มค่าและประสิทธิภาพเชิงวิศวกรรม

### ระยะที่ 1: การเพิ่มประสิทธิภาพระบบภายในเครื่อง (On-Device Architecture)
**เป้าหมาย:** ยกระดับประสบการณ์ใช้งานโดยไม่เพิ่มภาระค่าใช้จ่ายบริการภายนอก

1. **การแยกเสียงพูดออกจากเสียงประกอบ (Voice Activity Filtering)**
   - ปัญหาปัจจุบัน: เสียงดนตรีพื้นหลังและเอฟเฟกต์ในเกม (เสียงปืน, เสียงระเบิด) ส่งผลให้แบบจำลองถอดเสียงผิดพลาด
   - แนวทางพัฒนา: นำโมเดล DeepFilterNet หรือ Silero VAD มาคัดกรองเสียงก่อนส่งเข้ากระบวนการถอดเสียง เพื่อตัดเสียงรบกวนและเก็บเฉพาะย่านความถี่เสียงมนุษย์
   - ประโยชน์: ลดข้อผิดพลาดในการสะกดคำลงมากกว่า 50%

2. **การแสดงผลแบบสตรีมมิ่ง (Streaming Subtitle Pacing)**
   - ปัญหาปัจจุบัน: คำบรรยายจะปรากฏขึ้นเป็นก้อนหลังจากผู้พูดหยุดพูดเท่านั้น
   - แนวทางพัฒนา: ปรับวงจรการทำงานให้เป็นระบบสองสถานะ (Interim และ Final) โดยคำภาษาอังกฤษจะทยอยแสดงผลบนหน้าจอตามจังหวะการพูดสด จากนั้นระบบจะทบทวนและแปลเป็นภาษาไทยเมื่อจบวรรค
   - ประโยชน์: ลดความรู้สึกหน่วงของผู้ใช้งาน และสร้างจังหวะการอ่านที่ต่อเนื่องเหมือนคำบรรยายบนแพลตฟอร์มมาตรฐาน

### ระยะที่ 2: การเชื่อมต่อบริการคลาวด์เฉพาะทาง (Cloud-Based Integration)
**เป้าหมาย:** ยกระดับความแม่นยำและความเร็วสู่ระดับมาตรฐานเชิงพาณิชย์

1. **ระบบถอดรหัสเสียงผ่าน WebSocket Streaming (Speech-to-Text)**
   - แนวทางพัฒนา: เชื่อมต่อ Deepgram Nova หรือ Google Cloud Speech-to-Text v2 ผ่านสถาปัตยกรรม WebSocket
   - ประโยชน์:
     - ความหน่วงในการถอดรหัสเสียงลดลงเหลือประมาณ 150 ถึง 200 มิลลิวินาที
     - คืนทรัพยากรการประมวลผลให้การ์ดจอและซีพียู ทำให้เฟรมเรตในเกมคงที่
     - รองรับระบบ Keyword Boosting เพื่อกำหนดชื่อเฉพาะและศัพท์เทคนิคในเกม
   - รูปแบบค่าใช้จ่าย: คิดตามระยะเวลาการใช้งานจริง (ประมาณ 8 ถึง 10 บาทต่อชั่วโมงการเล่นเกม)

2. **ระบบแปลภาษาขั้นสูง (Contextual Translation Engine)**
   - แนวทางพัฒนา:
     - เชื่อมต่อ DeepL API สำหรับการแปลภาษาที่มีโครงสร้างไวยากรณ์สมบูรณ์
     - เชื่อมต่อ Large Language Model (เช่น Gemini Flash Paid Tier) เพื่อรองรับสำนวน แสลง และบทสนทนาเฉพาะกลุ่ม
   - ประโยชน์: สำนวนภาษาไทยมีความเป็นธรรมชาติ สละสลวย และตรงตามบริบทของเรื่องราว
   - รูปแบบค่าใช้จ่าย: ชำระตามปริมาณตัวอักษรจริง โดยเฉลี่ยไม่เกิน 30 ถึง 50 บาทต่อเดือนสำหรับการใช้งานทั่วไป

### ระยะที่ 3: ระบบออฟไลน์ประสิทธิภาพสูงระดับองค์กร (High-End Offline Inference)
**เป้าหมาย:** ความเป็นส่วนตัวสูงสุดและความเป็นอิสระจากการเชื่อมต่ออินเทอร์เน็ต

1. **การประมวลผลด้วยแบบจำลองขนาดใหญ่ในเครื่อง**
   - ข้อกำหนดระบบ: การ์ดประมวลผลกราฟิกที่มีหน่วยความจำ VRAM ขนาด 12GB ขึ้นไป (เช่น NVIDIA RTX ซีรีส์ 4070 ขึ้นไป)
   - แนวทางพัฒนา:
     - ติดตั้งแบบจำลอง Whisper Large-v3 Turbo สำหรับการถอดเสียงทุกสำเนียงโดยไม่สูญเสียความแม่นยำ
     - รันแบบจำลองภาษาขนาดเล็ก (SLM) ขนาด 7B ถึง 8B พารามิเตอร์ภายในเครื่องเพื่อทำหน้าที่แปลภาษาโดยตรง
   - ประโยชน์: ใช้งานได้โดยไม่ต้องพึ่งพาอินเทอร์เน็ต ความหน่วงคงที่ และไม่มีค่าใช้จ่ายรายเดือนในระยะยาว

### ดัชนีชี้วัดความสำเร็จของระบบ (Key Performance Indicators)

| ตัวชี้วัด | สถานะปัจจุบัน | เป้าหมายระยะที่ 1 | เป้าหมายระยะที่ 2 |
|---|---|---|---|
| ความหน่วงรวมทั้งระบบ (End-to-End Latency) | 600 - 800 ms | 400 - 500 ms | 250 - 350 ms |
| ความถูกต้องของคำศัพท์ในเกม (Domain Accuracy) | ปานกลาง | ดี | ดีเยี่ยม |
| การใช้ทรัพยากรเครื่องขณะเล่นเกม (GPU/CPU Load) | 15 - 25% | 15 - 20% | ต่ำกว่า 5% |
| ความเป็นธรรมชาติของบทแปล (BLEU / Human Score) | พอใช้ | พอใช้ | สูงมาก |

---

## ข้อแนะนำและการแก้ปัญหาเบื้องต้น (Troubleshooting)

- **การใช้งานคีย์ลัดในเกมบางเกมไม่ได้ผล:** บางเกมทำงานด้วยสิทธิ์ Administrator ให้เปิด PowerShell หรือ Command Prompt ด้วยสิทธิ์ "Run as Administrator" ก่อนรันโปรแกรม
- **ไม่มีเสียงหรือโปรแกรมตรวจไม่พบเสียง:** ตรวจสอบว่าเปิดเสียงในเกมหรือสื่ออยู่ และตรวจสอบว่า Default Audio Output ใน Windows ถูกเลือกไปยังอุปกรณ์ลำโพงหรือหูฟังที่กำลังฟังอยู่
- **การปรับแต่งคำศัพท์เฉพาะทาง:** สามารถเพิ่มคำศัพท์ ชื่อตัวละคร หรือชื่อสถานที่ในเกมลงในไฟล์ [glossary.json](file:///C:/Users/ASUS/realtime-game-translator/glossary.json) เพื่อให้ระบบจดจำและแปลได้ถูกต้องตามบริบท

---

## สัญญาอนุญาต (License)

โปรเจกต์นี้เผยแพร่ภายใต้สัญญาอนุญาต [MIT License](LICENSE)
