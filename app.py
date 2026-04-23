"""
Rockfall & Landslide Early Warning System — Server
===================================================
Flask + Flask-SocketIO + OpenCV (camera optional)
"""

import cv2
import numpy as np
import threading
import time
import socket as _socket
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit
import threading as _threading

# ── App Setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "rockfall-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Alert Thresholds ─────────────────────────────────────────────────────────
VIBRATION_LIMIT = 15
ANGLE_LIMIT = 30
CAMERA_CONTOUR_AREA = 5000

# ── Shared State ─────────────────────────────────────────────────────────────
latest_vibration = 0.0
latest_tilt = 0.0
camera_alert = False
camera_lock = threading.Lock()
camera_available = False

# ── OpenCV Camera (lazy init) ────────────────────────────────────────────────
camera = None
prev_frame = None


def init_camera():
    """Try to open the webcam. Returns True if successful."""
    global camera, camera_available
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            # Test-read one frame to confirm it really works
            ok, _ = cap.read()
            if ok:
                camera = cap
                camera_available = True
                print("[CAM] ✅ Camera opened successfully")
                return True
        cap.release()
        camera_available = False
        print("[CAM] ⚠  Camera not available — running in sensor-only mode")
        return False
    except Exception as e:
        camera_available = False
        print(f"[CAM] ⚠  Camera error: {e} — running in sensor-only mode")
        return False


def make_placeholder_frame(text="No Camera Connected"):
    """Generate a dark placeholder MJPEG frame."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (12, 15, 28)  # dark navy background

    # Outer border
    cv2.rectangle(frame, (8, 8), (632, 472), (50, 55, 90), 2)
    # Camera icon area
    cv2.rectangle(frame, (240, 170), (400, 270), (40, 45, 80), -1)
    cv2.rectangle(frame, (240, 170), (400, 270), (70, 75, 130), 2)
    # Lens circle
    cv2.circle(frame, (320, 220), 35, (60, 65, 110), -1)
    cv2.circle(frame, (320, 220), 35, (90, 95, 160), 2)
    cv2.circle(frame, (320, 220), 18, (40, 45, 80), -1)
    # Slash
    cv2.line(frame, (250, 175), (390, 265), (100, 50, 50), 3)

    # Text
    cv2.putText(frame, text, (170, 320),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (120, 125, 200), 2)
    cv2.putText(frame, "Sensor-only mode active", (165, 355),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 75, 130), 1)
    cv2.putText(frame, "Connect phone to stream live sensor data", (80, 390),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 65, 110), 1)

    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buffer.tobytes()


def generate_frames():
    """Yield MJPEG frames with motion-detection overlay."""
    global prev_frame, camera_alert

    # If camera not available, yield a static placeholder (low bandwidth)
    if not camera_available or camera is None:
        placeholder = make_placeholder_frame()
        frame_bytes = (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
        )
        while True:
            yield frame_bytes
            time.sleep(1.0)  # slow refresh — it's static
        return

    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(0.05)
            continue

        # Resize for performance
        frame = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_frame is None:
            prev_frame = gray
            continue

        # Frame differencing
        delta = cv2.absdiff(prev_frame, gray)
        thresh = cv2.threshold(delta, 30, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        motion_detected = False
        for c in contours:
            area = cv2.contourArea(c)
            if area > CAMERA_CONTOUR_AREA:
                motion_detected = True
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(
                    frame,
                    f"MOTION ({area:.0f})",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2,
                )

        with camera_lock:
            camera_alert = motion_detected

        # Status overlay
        status_color = (0, 0, 255) if motion_detected else (0, 255, 0)
        status_text = "MOTION DETECTED" if motion_detected else "Monitoring..."
        cv2.putText(
            frame, status_text, (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2,
        )

        prev_frame = gray

        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sensor")
def sensor_page():
    """Dedicated mobile-phone sensor page."""
    return render_template("sensor.html")


@app.route("/video")
def video():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/config")
def config():
    """Return server config as JSON for the frontend."""
    return jsonify({
        "vibration_limit": VIBRATION_LIMIT,
        "angle_limit": ANGLE_LIMIT,
        "camera_available": camera_available,
        "local_ip": get_local_ip(),
    })


@app.route("/ngrok-url")
def ngrok_url():
    """Try to read the active ngrok public URL from the local ngrok API."""
    import urllib.request, json as _json
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1) as r:
            data = _json.loads(r.read())
            for t in data.get("tunnels", []):
                if t.get("proto") == "https":
                    return jsonify({"url": t["public_url"] + "/sensor", "active": True})
        return jsonify({"active": False})
    except Exception:
        return jsonify({"active": False})


# ── WebSocket Events ────────────────────────────────────────────────────────
@socketio.on("connect")
def handle_connect():
    print("[WS] Client connected")
    # Send current state immediately on connect
    emit("server_info", {
        "camera_available": camera_available,
        "vibration_limit": VIBRATION_LIMIT,
        "angle_limit": ANGLE_LIMIT,
        "local_ip": get_local_ip(),
    })


@socketio.on("disconnect")
def handle_disconnect():
    print("[WS] Client disconnected")


@socketio.on("sensor_data")
def handle_sensor_data(data):
    global latest_vibration, latest_tilt

    vibration = float(data.get("vibration", 0))
    tilt = float(data.get("tilt", 0))

    latest_vibration = vibration
    latest_tilt = tilt

    with camera_lock:
        cam_alert = camera_alert

    # Determine alert
    alert = (
        vibration > VIBRATION_LIMIT
        or tilt > ANGLE_LIMIT
        or cam_alert
    )

    alert_reasons = []
    if vibration > VIBRATION_LIMIT:
        alert_reasons.append(f"Vibration {vibration:.1f} > {VIBRATION_LIMIT}")
    if tilt > ANGLE_LIMIT:
        alert_reasons.append(f"Tilt {tilt:.1f}° > {ANGLE_LIMIT}°")
    if cam_alert:
        alert_reasons.append("Camera motion detected")

    # Emit update to ALL connected clients
    socketio.emit("update", {
        "vibration": round(vibration, 2),
        "tilt": round(tilt, 2),
        "alert": alert,
        "camera_alert": cam_alert,
        "reasons": alert_reasons,
        "timestamp": time.time(),
    })


# ── Background: periodic camera-only alerts ─────────────────────────────────
def camera_alert_emitter():
    """Emit camera-only alerts even when no phone is connected."""
    while True:
        time.sleep(1)
        with camera_lock:
            cam = camera_alert
        if cam:
            socketio.emit("update", {
                "vibration": round(latest_vibration, 2),
                "tilt": round(latest_tilt, 2),
                "alert": True,
                "camera_alert": True,
                "reasons": ["Camera motion detected"],
                "timestamp": time.time(),
            })


# ── Helpers ──────────────────────────────────────────────────────────────────
def get_all_ips():
    """Return all non-loopback IPv4 addresses on this machine."""
    ips = []
    try:
        for iface in _socket.getaddrinfo(_socket.gethostname(), None):
            ip = iface[4][0]
            if ip.startswith("127.") or ":" in ip:
                continue
            if ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    # Also enumerate via ifconfig-style
    try:
        import subprocess
        out = subprocess.check_output(["ifconfig"], text=True)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet ") and "127.0.0.1" not in line:
                ip = line.split()[1]
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    return ips if ips else ["localhost"]


def get_local_ip():
    """Return best guess local IP (prefers 192.168.x.x)."""
    all_ips = get_all_ips()
    for ip in all_ips:
        if ip.startswith("192.168."):
            return ip
    return all_ips[0] if all_ips else "localhost"


def get_hostname():
    """Return mDNS hostname like sathyas-MacBook-Air.local"""
    try:
        return _socket.gethostname()
    except Exception:
        return "localhost"


# ── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_camera()
    t = _threading.Thread(target=camera_alert_emitter, daemon=True)
    t.start()

    hostname = get_hostname()
    all_ips  = get_all_ips()
    best_ip  = get_local_ip()

    print("\n" + "=" * 64)
    print("  🪨  Rockfall & Landslide Early Warning System")
    print("=" * 64)
    print(f"  📡  Dashboard (this laptop)  → https://localhost:5001")
    print()
    print("  📱  Open ONE of these on your phone:")
    print(f"      Hostname  → https://{hostname}:5001/sensor   ← try this first")
    for ip in all_ips:
        tag = " ← WiFi hotspot" if ip.startswith("192.168.") else ""
        print(f"      IP        → https://{ip}:5001/sensor{tag}")
    print()
    print("  ⚠️   Phone must be on the same WiFi / hotspot as this Mac")
    print("  ⚠️   You will see a 'Not Secure' warning. Tap 'Show Details' -> 'Visit this website' to proceed.")
    print("=" * 64 + "\n")
    socketio.run(app, host="0.0.0.0", port=5001, debug=False, ssl_context="adhoc")
