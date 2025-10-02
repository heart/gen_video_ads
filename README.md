![demo gif](ads.gif)

# การตั้งค่าและรันโปรเจ็กต์วิดีโอโฆษณา (Python)

## โปรเจ็กต์นี้ทำอะไร (Overview)

สคริปต์นี้ช่วย **สร้างสื่อโฆษณาแบบอัตโนมัติ** จาก “รูปบุคคล” และ “รูปสินค้า” แล้วต่อยอดไปเป็น

- **โปสเตอร์แนวโฆษณา** (Image) และ
- **วิดีโอแนวโฆษณาสั้น 9:16** (Video)

พร้อมรองรับ **2 แพลตฟอร์มโมเดล** ให้เลือกใช้งาน (เปิดได้พร้อมกันหรือทีละชุด):

1. **Google Gemini**

   - ใช้ `gemini-2.5-flash-image-preview` เพื่อสร้างโปสเตอร์จากรูปบุคคล + สินค้า
   - ใช้ `veo-3.0-generate-001` (ผ่าน Google AI Studio) เพื่อสร้างวิดีโอจากโปสเตอร์/ภาพอ้างอิง

2. **BytePlus ModelArk**
   - ใช้ `seedream-4-0-250828` เพื่อสร้างโปสเตอร์จากภาพอ้างอิง (data URL)
   - ใช้ `seedance-1-0-lite-i2v-250428` เพื่อแปลงภาพเป็นวิดีโอสั้น (image-to-video)

> โค้ดหลัก: `gen_video_ads.py` มี 2 ฟังก์ชัน flow — `run_gemini_flow()` และ `run_byteplus_flow()` ซึ่งจะถูกสั่งรัน **คู่ขนาน** ด้วย `ThreadPoolExecutor`

### อินพุตหลัก

- `PERSON_IMG_PATH` (เริ่มต้น: `heart.jpg`) – รูปใบหน้าหรือผู้พรีเซนต์
- `PRODUCT_IMG_PATH` (เริ่มต้น: `m150.jpg`) – รูปสินค้า (เช่น กระป๋อง/ขวดเครื่องดื่ม)

### เอาต์พุต

- โปสเตอร์ไฟล์ `.png` (ตั้งชื่อตาม timestamp)
- วิดีโอไฟล์ `.mp4` (ตั้งชื่อตาม task หรือ timestamp) พร้อมไฟล์ `.json` เก็บเมตาดาต้า (สำหรับ BytePlus flow)

### ฟีเจอร์สำคัญ

- รวมรูปบุคคล + รูปสินค้าเป็นภาพเดียวชั่วคราว (`combine_images`) เพื่อใช้เป็น reference
- สุ่มฉาก/บรรยากาศโฆษณาด้วย `create_poster_prompt()` เพื่อให้ได้งานที่หลากหลาย
- รองรับ **data URL** สำหรับส่งภาพเข้า API (จำเป็นต่อ BytePlus endpoint)
- ดึงผลลัพธ์ภาพ/วิดีโอแล้วบันทึกไฟล์ลงดิสก์ทันที

### โฟลว์การทำงานโดยย่อ

```
(คน + สินค้า) --> combine_images --> Poster (Gemini/BytePlus)
Poster --> Video (Gemini Veo-3 / BytePlus Seedance)
```

### ไฟล์/โมดูลที่เกี่ยวข้อง

- `gen_video_ads.py` – โค้ดหลักทั้งหมด
- ต้องมีไฟล์รูปอินพุต: `heart.jpg`, `m150.jpg` (หรือแก้ path ตามต้องการ)
- ใช้ไลบรารี: `google-genai`, `pillow`, `python-dotenv`, `requests`

### สิ่งที่ควรรู้

- ต้องตั้งค่า `.env` ให้ถูกต้อง (ดูด้านล่าง)
- บริการภายนอกอาจมี **ค่าใช้จ่าย** และ **โควตา** ตามแผนใช้งานของคุณ
- ระยะเวลาประมวลผลวิดีโอขึ้นอยู่กับคิวของผู้ให้บริการ (โค้ดมีการ poll สถานะงาน BytePlus ให้แล้ว)

### ข้อกำหนดด้านสิทธิ์/กฎหมาย

- ตรวจสอบสิทธิ์ในการใช้ภาพบุคคล/โลโก้/ผลิตภัณฑ์ก่อนใช้งานจริง
- หลีกเลี่ยงการทำให้โลโก้บิดเบี้ยว/ผิดแบรนด์ (มีคำสั่งในพรอมป์ทช่วยกำกับแล้วแต่ไม่การันตี 100%)
- เก็บรักษา API Key อย่างปลอดภัย ไม่ควร commit ลง Git

คู่มือนี้อธิบายขั้นตอนแบบสั้น กระชับ สำหรับติดตั้งสภาพแวดล้อม Python, ติดตั้ง dependencies, ตั้งค่าไฟล์ `.env` และรันสคริปต์หลัก

> ต้องมี **Python 3.10+** ในเครื่องก่อน

---

## 1) สร้าง Virtual Environment

```bash
python3 -m venv venv
```

## 2) เปิดใช้งาน (Activate)

- **macOS / Linux (bash/zsh):**

  ```bash
  source venv/bin/activate
  ```

- **Windows (PowerShell):**

  ```powershell
  .\venv\Scripts\Activate.ps1
  ```

- **Windows (Command Prompt/cmd):**
  ```bat
  .\venv\Scripts\activate.bat
  ```

> ปิดใช้งานเมื่อเสร็จงาน: `deactivate`

## 3) ติดตั้งแพ็กเกจที่ต้องใช้

```bash
pip install -r requirements.txt
```

## 4) ตั้งค่าไฟล์ `.env`

สร้างไฟล์ชื่อ `.env` ไว้ที่รากโปรเจ็กต์ แล้วกำหนดคีย์ดังนี้ (แทนที่ค่า `xxxxx`/`xxxx` ด้วยคีย์จริงของคุณ):

```
ARK_API_KEY=xxxxx
GEMINI_API_KEY=xxxx
```

### เอกสารทางการ: วิธีสร้าง/ขอ API Key

- **BytePlus ModelArk / ARK API Key** (หน้าจัดการ API Key):
  - https://docs.byteplus.com/en/docs/ModelArk/1361424
  - Quick Start (มีขั้นตอน “Obtaining and Configuring API Key”): https://docs.byteplus.com/en/docs/ModelArk/1399008
- **Google AI Studio (Gemini) – การสร้าง API Key:**
  - https://ai.google.dev/gemini-api/docs/api-key
  - (ลิงก์เข้าสร้างคีย์โดยตรง – ต้องล็อกอิน Google): https://aistudio.google.com/app/apikey

> หมายเหตุ: เก็บ API Key เป็นความลับ อย่า commit ลง Git

## 5) รันสคริปต์

```bash
python gen_video_ads.py
```

---

### เคล็ดลับแก้ปัญหาทั่วไป

- ถ้า `pip` ช้า/ติด proxy ลองอัปเกรด pip: `python -m pip install -U pip`
- ถ้าพบว่า `python` ชี้ไปเวอร์ชันเก่า ให้ใช้ `py -3` (บน Windows) หรือ `python3` (macOS/Linux)
- หากสคริปต์ต้องอ่าน `.env` ตรวจสอบว่ามีการโหลดด้วยไลบรารีเช่น `python-dotenv` แล้ว (`pip install python-dotenv` หากยังไม่ได้ติดตั้ง)
