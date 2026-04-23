# 🪨 Rockfall & Landslide Early Warning System

A real-time monitoring dashboard and mobile sensor system. It turns your mobile phone into a live vibration and tilt sensor while using your laptop's camera for motion detection.

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
Make sure you have Python installed, then install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Generate Alert Sounds (Optional)
If you are missing the alert sound file, you can generate it using:
```bash
python generate_alert_sound.py
```

### 3. Run the Server
Start the Flask application:
```bash
python app.py
```

---

## 📱 How to Connect Your Phone (Mobile Sensor)

Since the system needs to read live motion sensors from your phone, your phone must be on the same local network as your laptop.

### Step 1: Connect to the same network
* **Option A (Best):** Connect your laptop and phone to the exact same Wi-Fi network.
* **Option B (Hotspot):** Turn on your Mac's Wi-Fi hotspot (`System Settings -> General -> Sharing -> Internet Sharing`) and connect your phone to it.

### Step 2: Open the Dashboard
On your **laptop**, open your web browser and go to:
👉 **`https://localhost:5001`**

*(Note: Because this is a local HTTPS server, your browser will say "Connection is not private". Click **Advanced / Show Details** and then **Proceed / Visit this website**).*

### Step 3: Connect your Phone
Look at the terminal output where you ran `python app.py`, or look at the QR code section on the dashboard.
Type the provided URL into **Safari** on your iPhone or **Chrome** on Android. It will look something like this:
👉 `https://192.168.2.1:5001/sensor`

### Step 4: Grant Permissions
* **On iPhone:** A splash screen will appear. Tap anywhere on the screen, then tap **"Allow"** when prompted for Motion & Orientation access.
* **On Android:** The sensors will start streaming automatically after 1 second.

Keep the browser tab open on your phone, move your device around, and watch the values update in real-time on your laptop dashboard!

---

## ⚙️ How it Works
- **Flask & Socket.IO:** Powers the backend server and handles real-time bidirectional streaming.
- **OpenCV:** Reads the laptop webcam to detect motion outlines and threshold breaches.
- **JavaScript `DeviceMotionEvent`:** Reads the raw accelerometer and gyroscope data from the connected mobile phone.
- **Adhoc SSL:** Automatically generates local HTTPS certificates so iOS browsers permit sensor data access.
