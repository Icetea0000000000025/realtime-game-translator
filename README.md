# 🎮 Real-Time Game Translator (EN ➔ TH)

โปรแกรมแปลภาษาเกมเนื้อเรื่องแบบ Real-Time จากภาษาอังกฤษเป็นภาษาไทย พร้อมระบบ Transparent Subtitle Overlay แสดงผลทับบนหน้าจอเกมแบบไม่สะดุด

---

## ✨ Features (คุณสมบัติเด่น)

- 📸 **Fast Screen Capture**: จับภาพหน้าจอเฉพาะส่วน (Region of Interest - ROI) เช่น กล่องบทพูด หรือ ซับไตเติล
- 🔍 **Real-time OCR**: แกะตัวอักษรภาษาอังกฤษจากภาพในเกมด้วยความแม่นยำสูง
- 🌐 **Multi-Engine Translation**: รองรับทั้ง Google Translate (`deep-translator`) และ AI LLM (Gemini / GPT) เพื่อสำนวนที่เป็นธรรมชาติ
- 🪟 **Transparent Overlay**: หน้าต่างแสดงคำแปลภาษาไทยแบบโปร่งใส ลอยอยู่เหนือเกม (Click-through / ปักหมุดบนสุด)
- ⚡ **Debounce / Text Change Detection**: ไม่สั่งแปลซ้ำหากข้อความยังไม่เปลี่ยน ช่วยประหยัดทรัพยากรและลด Delay
- ⌨️ **Hotkey Shortcuts**: ควบคุมเปิด/ปิดการแปล หรือเลือกพื้นที่ได้ง่ายด้วยคีย์ลัด

---

## 🏗️ Architecture (สถาปัตยกรรมระบบ)

```
[ Game Screen ] 
       │
       ▼ (mss / WinAPI)
[ Screen Capture ROI ] 
       │
       ▼ (OpenCV Preprocessing)
[ OCR Engine (PaddleOCR / EasyOCR / Windows OCR) ] 
       │ (Extracted English Text)
       ▼ (Text Change Detector & Cache)
[ Translation Engine (Google / Gemini API) ] 
       │ (Translated Thai Subtitles)
       ▼
[ PyQt6 Transparent Overlay ] 
```

---

## 📦 Project Structure (โครงสร้างโปรเจกต์)

```
realtime-game-translator/
├── src/
│   ├── capture.py        # ระบบจับภาพหน้าจอ (Screen capture)
│   ├── ocr.py            # ระบบอ่านตัวอักษร (OCR Engine)
│   ├── translator.py     # ระบบแปลภาษา (Translation service)
│   ├── overlay.py        # หน้าต่าง Overlay แสดงผลซับไตเติล
│   └── utils.py          # ฟังก์ชันช่วยเหลือ & Image Preprocessing
├── main.py               # จุดเริ่มต้นรันโปรแกรม
├── requirements.txt      # รายการไลบรารีที่จำเป็น
├── .gitignore            # ไฟล์ที่ไม่ต้องดันขึ้น Git
└── README.md             # รายละเอียดโปรเจกต์
```

---

## 🚀 Getting Started (วิธีติดตั้งและใช้งาน)

### 1. Clone Repository & Setup
```bash
git clone https://github.com/<YOUR_USERNAME>/realtime-game-translator.git
cd realtime-game-translator
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Application
```bash
python main.py
```

---

## 🗺️ Roadmap (แผนการพัฒนา)

- [x] Initial project structure & setup
- [ ] Implement Fast Screen Capture module (ROI selection)
- [ ] Implement OCR Engine with Image Preprocessing
- [ ] Implement Translation Engine (Google & Gemini API support)
- [ ] Implement Transparent Click-Through Subtitle Overlay (PyQt6)
- [ ] Add Global Hotkeys & UI Settings Panel
- [ ] Packaging as standalone executable (.exe)

---

## 📄 License
This project is licensed under the MIT License.
