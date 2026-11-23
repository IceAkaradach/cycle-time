"""
Cycle Time Video AI Server
ให้หน้าเว็บ index.html เชื่อมต่อเพื่อวิเคราะห์ตัดรอบเวลาวิดีโอด้วย Python OpenCV
"""
import http.server
import socketserver
import json
import os
import tempfile
import uuid
from urllib.parse import unquote
import cv2
import numpy as np

PORT = int(os.environ.get("PORT", "8765"))
MAX_UPLOAD_BYTES = 4 * 1024 * 1024 * 1024
UPLOADS = {}

class CycleTimeHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Allow CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Video-Name')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self.send_json(200, {"service": "cycle-time", "status": "ok"})
            return
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/upload_video':
            content_length = int(self.headers.get('Content-Length', 0))
            original_name = os.path.basename(unquote(self.headers.get('X-Video-Name', 'video.mp4')))
            extension = os.path.splitext(original_name)[1].lower()
            if extension not in ('.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm'):
                self.send_json(400, {"error": "ชนิดไฟล์วิดีโอไม่รองรับ"})
                return
            if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
                self.send_json(413, {"error": "ไฟล์วิดีโอว่างหรือมีขนาดเกิน 4 GB"})
                return

            token = uuid.uuid4().hex
            target = os.path.join(tempfile.gettempdir(), f"cycle-time-{token}{extension}")
            remaining = content_length
            try:
                with open(target, 'wb') as output:
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError("ข้อมูลวิดีโอสิ้นสุดก่อนครบขนาดที่ระบุ")
                        output.write(chunk)
                        remaining -= len(chunk)
                UPLOADS[token] = target
                self.send_json(200, {"success": True, "video_token": token})
            except ValueError as e:
                if os.path.exists(target):
                    os.remove(target)
                self.send_json(400, {"error": str(e)})
                return
            except Exception as e:
                if os.path.exists(target):
                    os.remove(target)
                self.send_json(400, {"error": str(e)})
            return
        elif self.path == '/api/export_template_excel':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                from api.export_template_excel import generate_excel_from_template
                req = json.loads(post_data.decode('utf-8'))
                excel_bytes = generate_excel_from_template(req)

                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Length', str(len(excel_bytes)))
                self.end_headers()
                self.wfile.write(excel_bytes)
                print(f"📊 ส่งออกไฟล์ Excel สำเร็จตามแม่แบบ Time.xlsx 100% พร้อมกราฟ SWCT และ YAMAZUMI!")
                return
            except ValueError as e:
                self.send_json(400, {"error": str(e)})
                return
            except Exception as e:
                print(f"❌ Error Exporting Excel: {e}")
                import traceback
                traceback.print_exc()
                self.send_json(500, {"error": "ไม่สามารถสร้างไฟล์ Excel ได้"})
                return
        elif self.path == '/api/analyze_cycles':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                req = json.loads(post_data.decode('utf-8'))
                video_name = req.get('video_name')
                video_token = req.get('video_token')
                first_round_cycles = req.get('first_round_cycles', []) # รายการของรอบที่ 1 ที่ผู้ใช้จับไว้
                
                print(f"\n📡 ได้รับคำสั่งวิเคราะห์วิดีโอ: {video_name}")
                print(f"📌 ข้อมูลรอบที่ 1 ที่ส่งมา: {len(first_round_cycles)} ขั้นตอน")

                target_video = UPLOADS.pop(video_token, None) if video_token else None
                if not target_video and video_name:
                    candidate = os.path.abspath(os.path.basename(video_name))
                    if os.path.isfile(candidate) and candidate.lower().endswith(('.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm')):
                        target_video = candidate

                if not target_video:
                    self.send_json(404, {"error": "ไม่พบวิดีโอที่เลือก กรุณาเลือกหรืออัปโหลดไฟล์อีกครั้ง"})
                    return

                print(f"🎬 กำลังประมวลผลไฟล์: {target_video}")

                # ประมวลผลและสร้างรอบเวลาที่เหลือ
                try:
                    result_cycles = run_motion_tracking(target_video, first_round_cycles)
                finally:
                    if video_token and os.path.exists(target_video):
                        os.remove(target_video)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "cycles": result_cycles}, ensure_ascii=False).encode('utf-8'))

            except ValueError as e:
                print(f"❌ Invalid analysis request: {e}")
                self.send_json(422, {"error": str(e)})
            except Exception as e:
                print(f"❌ Error: {e}")
                self.send_json(500, {"error": "เกิดข้อผิดพลาดระหว่างวิเคราะห์วิดีโอ"})
        else:
            super().do_POST()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def run_motion_tracking(video_file, first_round):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        cap.release()
        raise ValueError("ไม่สามารถเปิดวิดีโอได้ อาจเป็นไฟล์เสียหรือ codec ไม่รองรับ")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_dur = total_frames / fps
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # ถ้ามี cached timeline ให้ใช้ก่อนเพื่อความเร็วสูง
    timeline = []
    cache_file = "full_mov_timeline.json" if os.path.basename(video_file) == "ขั้นตอน 9.mov" else None
    cache_is_fresh = cache_file and os.path.exists(cache_file) and os.path.getmtime(cache_file) >= os.path.getmtime(video_file)
    if cache_is_fresh:
        with open(cache_file, "r", encoding="utf-8") as f:
            timeline = json.load(f)
        cap.release()
    else:
        # สแกนสด
        ret, prev = cap.read()
        if not ret or prev is None:
            cap.release()
            raise ValueError("วิดีโอไม่มีเฟรมที่อ่านได้")
        prev_gray = cv2.GaussianBlur(cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY), (9, 9), 0)
        fc = 0
        step = 6
        pick_zone = (int(0.05 * w), int(0.12 * h), int(0.38 * w), int(0.48 * h))
        while True:
            ret, frame = cap.read()
            if not ret: break
            fc += 1
            if fc % step != 0: continue
            cur_sec = fc / fps
            gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (9, 9), 0)
            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
            roi = thresh[pick_zone[1]:pick_zone[1]+pick_zone[3], pick_zone[0]:pick_zone[0]+pick_zone[2]]
            timeline.append({"time": cur_sec, "energy": {"pick_main": float(np.mean(roi) / 255.0 * 100.0)}})
            prev_gray = gray
        cap.release()

    if not timeline:
        raise ValueError("วิดีโอสั้นเกินไปหรือไม่พบเฟรมสำหรับวิเคราะห์")

    times = np.array([p["time"] for p in timeline])
    pick_e = np.array([p["energy"]["pick_main"] for p in timeline])
    pick_s = np.convolve(pick_e, np.ones(5)/5, mode='same')

    # คำนวณช่วงเวลาและสัดส่วนของแต่ละขั้นตอนในรอบที่ 1
    if not first_round:
        # ค่าเริ่มต้นสำหรับงานเย็บผ้า 4 ขั้นตอนมาตรฐาน
        first_round = [
            {"step": "1.หยิบmain", "duration": 5.73},
            {"step": "2.หยิบผ้า", "duration": 6.02},
            {"step": "3.เย็บ", "duration": 42.36},
            {"step": "4.ตรวจ", "duration": 5.03}
        ]
        start_anchor = 178.27
    else:
        start_anchor = first_round[0].get("start", 178.27)

    steps_template = [c["step"] for c in first_round]
    durations_template = [float(c.get("duration", 5.0)) for c in first_round]
    if any(not np.isfinite(d) or d <= 0 for d in durations_template):
        raise ValueError("ระยะเวลาของทุกขั้นตอนในรอบแรกต้องเป็นตัวเลขมากกว่า 0")
    total_template_dur = sum(durations_template) or 60.0
    ratios = [d / total_template_dur for d in durations_template]

    # ตรวจจับจุดเริ่มของแต่ละรอบใหญ่ (Cycle Starts)
    cycle_starts = [start_anchor]
    curr = start_anchor

    while curr < times[-1] - 40.0:
        min_gap = max(45.0, total_template_dur * 0.75)
        max_gap = min(120.0, total_template_dur * 1.50)
        idx_win = np.where((times >= curr + min_gap) & (times <= curr + max_gap))[0]
        if len(idx_win) == 0:
            break
        best_idx = idx_win[np.argmax(pick_s[idx_win])]
        best_t = float(times[best_idx])
        cycle_starts.append(round(best_t, 2))
        curr = best_t

    if cycle_starts[-1] < times[-1] - 15.0:
        cycle_starts.append(round(times[-1], 2))

    # สร้างรายการรอบและขั้นตอนทั้งหมดส่งกลับให้หน้าเว็บ
    generated_cycles = []
    global_cycle_no = 1

    for r_idx in range(len(cycle_starts) - 1):
        round_no = r_idx + 1
        r_start = cycle_starts[r_idx]
        r_end = cycle_starts[r_idx + 1]
        r_dur = r_end - r_start

        # แบ่งขั้นตอนย่อยตามสัดส่วนของแม่แบบรอบที่ 1
        sub_start = r_start
        for s_idx, (step_name, ratio) in enumerate(zip(steps_template, ratios)):
            step_dur = round(r_dur * ratio, 2)
            sub_end = round(sub_start + step_dur, 2)
            if s_idx == len(steps_template) - 1:
                sub_end = r_end
                step_dur = round(sub_end - sub_start, 2)

            generated_cycles.append({
                "no": global_cycle_no,
                "cycleRound": round_no,
                "elementNo": s_idx + 1,
                "step": step_name,
                "start": round(sub_start, 2),
                "end": round(sub_end, 2),
                "duration": round(step_dur, 2),
                "note": f"AI Python Auto-Tracked (รอบที่ {round_no})"
            })
            global_cycle_no += 1
            sub_start = sub_end

    print(f"🎉 สร้างขั้นตอนอัตโนมัติสำเร็จ {len(generated_cycles)} รายการ ({len(cycle_starts)-1} รอบ)")
    return generated_cycles

if __name__ == '__main__':
    HOST = os.environ.get("HOST", "127.0.0.1")
    print(f"🚀 เริ่มรัน Cycle Time Server บน http://{HOST}:{PORT}")
    print(f"👉 เปิดเบราว์เซอร์ไปที่: http://{HOST}:{PORT}/index.html")
    server = socketserver.ThreadingTCPServer((HOST, PORT), CycleTimeHandler)
    server.daemon_threads = True
    server.serve_forever()
