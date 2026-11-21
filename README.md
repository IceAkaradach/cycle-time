# Cycle Time Video Study & SWCT Generator ⏱️📊

เว็บแอปพลิเคชันและเครื่องมือสำหรับวิเคราะห์และจับเวลาการทำงาน (Cycle Time Video Study) จากวิดีโอ พร้อมทั้งคำนวณและสร้างเอกสาร **Standardized Work Combination Table (SWCT)** ออกมาเป็นไฟล์ Excel (`.xlsx`) ตามแบบฟอร์มมาตรฐานอย่างแม่นยำ 100% พร้อมกราฟ Gantt chart / Bar chart จำแนกขั้นตอนการทำงาน

---

## 🌟 ฟีเจอร์เด่น (Key Features)

1. **Video Player & Dual-Source Loading (รองรับทั้งไฟล์ในเครื่องและ OneDrive):**
   - โหลดวิดีโอจากเครื่อง (`.mp4`, `.mov`, ฯลฯ) ไม่จำกัดขนาด
   - **ดึงวิดีโอจาก URL / Cloud ได้โดยตรง:** รองรับลิงก์แชร์จาก **OneDrive, SharePoint**, Google Drive, Dropbox หรือ Direct Video URL พร้อมระบบแปลงลิงก์เป็น Direct Stream อัตโนมัติ
   - มีปุ่ม **"สลับ URL"** เปลี่ยนแหล่งวิดีโอระหว่างการทำงานได้ทันทีโดยไม่สูญเสียข้อมูลที่จับไว้
   - ปรับความเร็ววิดีโอได้ตั้งแต่ `0.1x` ถึง `5.0x` เพื่อการจับเวลาที่แม่นยำระดับเฟรม
   - Hotkeys รองรับการควบคุมด้วยคีย์บอร์ดอย่างรวดเร็ว:
     - `Spacebar`: เริ่ม / บันทึกขั้นตอน (Start / Save Cycle)
     - `P`: เล่น / หยุดวิดีโอชั่วคราว (Play / Pause)
     - `ลูกศร ซ้าย / ขวา (← / →)`: ก้าวทีละเฟรม (0.05s) หรือ `Shift + (← / →)` สำหรับ 1 วินาที
     - `[` / `]`: ปรับลด / เพิ่มความเร็วการเล่น (0.1x ถึง 5.0x)
     - `R`: ย้อนกลับไปจุดเริ่มต้น (00:00)
     - `Q`: บันทึกและเสร็จสิ้นเซสชัน เข้าสู่หน้า Export Excel

2. **Cycle Time & Process Step Tracking:**
   - กำหนดขั้นตอนการทำงาน (Process Steps) พร้อมเลือกชื่อขั้นตอน / หมายเลขลำดับอัตโนมัติ
   - ปุ่มลัด **START CYCLE / RECORD STEP** จับเวลาได้ทันที
   - รองรับการแบ่งรอบ (Cycle Round) เพื่อจับเวลาหลายรอบเปรียบเทียบกัน

3. **SWCT Graph & Criteria Selection:**
   - คำนวณเวลารอบ (Cycle Time) และเลือกรอบที่จะนำไปพล็อตกราฟ SWCT ได้:
     - เลือกรอบที่เวลาน้อยที่สุด (Min / Best Cycle)
     - เลือกรอบที่เวลามากที่สุด (Max Cycle)
     - เลือกรอบเฉลี่ย (Average) หรือระบุรอบเองได้
   - ปรับสเกลแกนเวลาของกราฟ SWCT แบบไดนามิก (Dynamic Time Axis Scaling) ตามเวลา Cycle Time จริง

4. **Excel Export (Standardized Work Combination Table):**
   - ส่งออกข้อมูลลงในแม่แบบ `Time.xlsx` สมบูรณ์แบบ 100% ทั้งฟอร์มและสูตร
   - รองรับ 2 โหมดการทำงาน:
     - **Serverless / Python Backend**: ประมวลผลแก้ไข XML ภายในไฟล์ Excel โดยตรง
     - **Offline / Client-Side**: ทำงานผ่านเบราว์เซอร์ได้ทันทีโดยไม่ต้องต่ออินเทอร์เน็ต ด้วย JSZip + Base64 Template

---

## 🚀 วิธีการใช้งาน (Getting Started)

### 1. ใช้งานผ่านเว็บ (Web Application / Vercel)
สามารถเปิดใช้งานผ่าน Web Browser ได้ทันทีโดยไม่ต้องติดตั้งโปรแกรมใดๆ

### 2. รันบนเครื่องคอมพิวเตอร์ (Local Setup)

#### สำหรับ macOS:
ดับเบิลคลิกที่ไฟล์:
- **`Start Cycle Time.app`** หรือ **`Start_Cycle_Time.command`**
ระบบจะเปิดเว็บเบราว์เซอร์พร้อมรัน Local Server ให้อัตโนมัติ

#### หรือรันผ่าน Terminal:
```bash
# ติดตั้ง dependencies (หากต้องการใช้ backend python server)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# รัน Server
python3 app_server.py
```
เปิดเบราว์เซอร์ไปที่: `http://localhost:8000`

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```text
├── index.html                   # หน้าเว็บแอปพลิเคชันหลัก (Single Page Application)
├── time_template_b64.js         # Base64 Template สำหรับ Offline In-Browser Excel Export
├── Time.xlsx                    # ไฟล์แม่แบบมาตรฐาน SWCT (Excel Template)
├── app_server.py                # Local Python Server
├── requirements.txt             # รายการ Python dependencies (OpenCV, NumPy)
├── Start Cycle Time.app         # แอปรันสำหรับ macOS (One-click launch)
├── Start_Cycle_Time.command     # สคริปต์รันสำหรับ macOS
├── api/
│   ├── export_template_excel.py # Vercel Serverless Function สำหรับ Export Excel
│   └── Time.xlsx                # แม่แบบ Excel สำรองสำหรับ Serverless
├── vercel.json                  # การตั้งค่าการ Deploy บน Vercel
└── package.json                 # ข้อมูลโปรเจกต์สำหรับ npm / Vercel
```

---

## 📄 License
MIT License
