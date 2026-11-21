import cv2
import numpy as np
import json
import time

video_path = "ขั้นตอน 9.mov"
cap = cv2.VideoCapture(video_path)

fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"🎬 กำลังสแกนไฟล์ ขั้นตอน 9.mov: {w}x{h} @ {fps:.1f}fps, {total_frames} เฟรม ({total_frames/fps:.1f} วินาที)")

# โซนวิเคราะห์ 4 จุดสำคัญ
zones = {
    # 1. โซนหยิบชิ้นงานชิ้นใหญ่ (ซ้ายบน)
    "pick_main": (int(0.05 * w), int(0.12 * h), int(0.38 * w), int(0.48 * h)),
    # 2. โซนหน้าเข็มจักร (ตรวจจับการเดินเข็มเย็บต่อเนื่อง)
    "needle":    (int(0.50 * w), int(0.42 * h), int(0.40 * w), int(0.45 * h)),
    # 3. โซนแท่นวางผ้าหน้าตัวคนงาน (ตรวจจับการคลี่/จัดผ้า)
    "table_front": (int(0.22 * w), int(0.45 * h), int(0.35 * w), int(0.50 * h)),
    # 4. โซนมือขวาตรวจชิ้นงาน / ตัดด้าย
    "inspect":   (int(0.35 * w), int(0.30 * h), int(0.45 * w), int(0.45 * h))
}

ret, prev_frame = cap.read()
if not ret:
    print("❌ ไม่สามารถเปิดวิดีโอได้")
    exit(1)

prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
prev_gray = cv2.GaussianBlur(prev_gray, (9, 9), 0)

sample_step = 6  # สแกนทุก 6 เฟรม (5 ตัวอย่างต่อวินาที = 0.2s resolution) แม่นยำและรันได้เร็วมาก
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

    diff = cv2.absdiff(prev_gray, gray)
    _, thresh = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)

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

    if frame_count % 3000 == 0:
        percent = (frame_count / total_frames) * 100
        elapsed = time.time() - start_time
        print(f"⏳ สแกนไปแล้ว {percent:.1f}% ({current_sec:.1f}s / {total_frames/fps:.1f}s) ใช้เวลา {elapsed:.1f}s")

cap.release()
print(f"✅ สแกนวิดีโอ 17.6 นาทีเสร็จสิ้น! ได้ {len(timeline)} จุดข้อมูล ใช้เวลา {time.time() - start_time:.1f} วินาที")

with open("full_mov_timeline.json", "w", encoding="utf-8") as f:
    json.dump(timeline, f)

print("💾 บันทึก full_mov_timeline.json เรียบร้อย")
