import cv2
import numpy as np
import json
import time

video_path = "ขั้นตอนที่ 9.2.mp4"
cap = cv2.VideoCapture(video_path)

fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"🎬 กำลังวิเคราะห์วิดีโอ: {w}x{h} @ {fps:.1f}fps, ทั้งหมด {total_frames} เฟรม ({total_frames/fps:.1f} วินาที)")

# กำหนด 3 โซนหลักสำหรับงานจักรเย็บผ้า:
# 1. โซนหยิบชิ้นงาน (Pick Zone): กองผ้าด้านซ้าย
# 2. โซนหน้าเข็มจักร (Needle Zone): บริเวณหัวจักรและเข็ม
# 3. โซนจัดผ้า/ส่งผ้า (Feed Zone): บริเวณด้านหน้าตัวคนงาน
zones = {
    "pick":   (int(0.05 * w), int(0.15 * h), int(0.40 * w), int(0.55 * h)),
    "needle": (int(0.48 * w), int(0.40 * h), int(0.45 * w), int(0.50 * h)),
    "feed":   (int(0.20 * w), int(0.45 * h), int(0.40 * w), int(0.50 * h))
}

ret, prev_frame = cap.read()
if not ret:
    print("❌ ไม่สามารถเปิดวิดีโอได้")
    exit(1)

prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
prev_gray = cv2.GaussianBlur(prev_gray, (9, 9), 0)

# เก็บข้อมูลทุกๆ 3 เฟรม (10 ครั้งต่อวินาที) เพื่อความรวดเร็วและแม่นยำสูง
sample_step = 3
timeline = []

frame_count = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1

    if frame_count % sample_step != 0:
        continue

    current_sec = frame_count / fps
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 0)

    # Frame Differencing + Optical thresholding
    diff = cv2.absdiff(prev_gray, gray)
    _, thresh = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)

    # คำนวณพลังงานการเคลื่อนไหวในแต่ละโซน
    zone_energy = {}
    for z_name, (zx, zy, zw, zh) in zones.items():
        roi = thresh[zy:zy+zh, zx:zx+zw]
        energy = float(np.mean(roi) / 255.0 * 100.0)
        zone_energy[z_name] = round(energy, 2)

    timeline.append({
        "time": round(current_sec, 2),
        "frame": frame_count,
        "energy": zone_energy
    })

    prev_gray = gray

    if frame_count % 900 == 0:
        percent = (frame_count / total_frames) * 100
        elapsed = time.time() - start_time
        print(f"⏳ ประมวลผลไปแล้ว {percent:.1f}% ({current_sec:.1f}s / {total_frames/fps:.1f}s) ใช้เวลา {elapsed:.1f}s")

cap.release()
print(f"✅ ประมวลผลภาพเสร็จสิ้น! ได้ {len(timeline)} ตัวอย่าง ใช้เวลารวม {time.time() - start_time:.1f}s")

# บันทึก Timeline ดิบ
with open("motion_timeline.json", "w", encoding="utf-8") as f:
    json.dump(timeline, f, ensure_ascii=False)

print("💾 บันทึก motion_timeline.json เรียบร้อย")
