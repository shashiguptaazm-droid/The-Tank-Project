/*
 * USBVideoCamera.ino - DFRobot ESP32-S3 AI Camera V1.1
 * 
 * Streams JPEG frames over USB serial (CDC) for uninterrupted video.
 * No WiFi needed — direct USB connection to Jetson.
 * 
 * Protocol (USB Serial 921600 baud):
 *   Host → Camera:  "SNAP\n"    = capture single frame
 *   Host → Camera:  "STREAM\n"  = start continuous streaming
 *   Host → Camera:  "STOP\n"    = stop streaming
 *   Host → Camera:  "RES <n>\n" = set resolution (5=QVGA, 8=VGA, 9=SVGA, 10=XGA)
 *   Host → Camera:  "QUAL <n>\n"= set JPEG quality (0-63, lower=better)
 *   Host → Camera:  "LED <0/1>\n"= toggle LED
 *   Host → Camera:  "IMU\n"     = request IMU data
 *   Host → Camera:  "STATUS\n"  = request status
 *   Host → Camera:  "HELP\n"    = list commands
 *   
 *   Camera → Host:  "FRAME:<width>:<height>:<size>:<jpeg_bytes>\n"  (binary JPEG follows)
 *   Camera → Host:  "IMU:<x>:<y>:<z>\n"
 *   Camera → Host:  "OK:<message>\n"
 *   Camera → Host:  "ERR:<message>\n"
 *
 * Arduino IDE Settings:
 *   USB CDC on Boot: Enabled
 *   CPU Frequency: 240 MHz (WiFi)
 *   Flash Mode: QIO 80 MHz
 *   Flash Size: 16 MB
 *   PSRAM: OPI PSRAM
 *   Partition Scheme: Huge App (3MB No OTA)
 */

#include "esp_camera.h"
#include <Wire.h>

// ============== CAMERA PIN CONFIGURATION (DFRobot ESP32-S3 AI Camera V1.1) ==============
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     5
#define Y9_GPIO_NUM       4
#define Y8_GPIO_NUM       6
#define Y7_GPIO_NUM       7
#define Y6_GPIO_NUM       14
#define Y5_GPIO_NUM       17
#define Y4_GPIO_NUM       21
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       16
#define VSYNC_GPIO_NUM    1
#define HREF_GPIO_NUM     2
#define PCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM     8
#define SIOC_GPIO_NUM     9
#define LED_GPIO_NUM      47

// ============== IMU (onboard QMI8658) ==============
#define QMI8658_ADDR 0x6B

// ============== GLOBALS ==============
bool streaming = false;
unsigned long lastFrameTime = 0;
unsigned long frameCount = 0;
int targetFps = 10;  // target frames per second

// ============== IMU ==============
float imuAccX = 0, imuAccY = 0, imuAccZ = 0;
float imuGyrX = 0, imuGyrY = 0, imuGyrZ = 0;

void initIMU() {
  Wire.begin(SIOD_GPIO_NUM, SIOC_GPIO_NUM);
  
  // Check if QMI8658 is present
  Wire.beginTransmission(QMI8658_ADDR);
  if (Wire.endTransmission() == 0) {
    // Reset
    Wire.beginTransmission(QMI8658_ADDR);
    Wire.write(0x60); // Ctrl
    Wire.write(0x0B); // Reset
    Wire.endTransmission();
    delay(100);
    
    // Enable accelerometer + gyroscope
    Wire.beginTransmission(QMI8658_ADDR);
    Wire.write(0x02); // Ctrl2
    Wire.write(0x30); // Accel ODR 250Hz, range ±8g
    Wire.endTransmission();
    
    Wire.beginTransmission(QMI8658_ADDR);
    Wire.write(0x03); // Ctrl3
    Wire.write(0x30); // Gyro ODR 250Hz, range ±512dps
    Wire.endTransmission();
    
    // Enable sensors
    Wire.beginTransmission(QMI8658_ADDR);
    Wire.write(0x06); // Ctrl7
    Wire.write(0x03); // Enable acc + gyro
    Wire.endTransmission();
    
    Serial.println("OK:QMI8658 IMU initialized");
  } else {
    Serial.println("OK:No IMU found (QMI8658 not responding)");
  }
}

void readIMU() {
  // Read accelerometer
  Wire.beginTransmission(QMI8658_ADDR);
  Wire.write(0x35); // Accel X low
  Wire.endTransmission();
  Wire.requestFrom(QMI8658_ADDR, 6);
  if (Wire.available() == 6) {
    int16_t ax = Wire.read() | (Wire.read() << 8);
    int16_t ay = Wire.read() | (Wire.read() << 8);
    int16_t az = Wire.read() | (Wire.read() << 8);
    imuAccX = ax / 4096.0; // ±8g
    imuAccY = ay / 4096.0;
    imuAccZ = az / 4096.0;
  }
  
  // Read gyroscope
  Wire.beginTransmission(QMI8658_ADDR);
  Wire.write(0x3B); // Gyro X low
  Wire.endTransmission();
  Wire.requestFrom(QMI8658_ADDR, 6);
  if (Wire.available() == 6) {
    int16_t gx = Wire.read() | (Wire.read() << 8);
    int16_t gy = Wire.read() | (Wire.read() << 8);
    int16_t gz = Wire.read() | (Wire.read() << 8);
    imuGyrX = gx / 512.0;  // ±512dps
    imuGyrY = gy / 512.0;
    imuGyrZ = gz / 512.0;
  }
}

// ============== CAMERA ==============
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_VGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  if (psramFound()) {
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
    Serial.println("OK:PSRAM found, dual-buffer mode");
  } else {
    Serial.println("OK:No PSRAM, single-buffer mode");
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("ERR:Camera init failed 0x%x\n", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_vflip(s, 1);
    s->set_brightness(s, 1);
    s->set_framesize(s, FRAMESIZE_VGA);
    Serial.printf("OK:Camera ready PID=0x%02X\n", s->id.PID);
  }
}

// ============== FRAME CAPTURE & SEND ==============
void sendFrame() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("ERR:Capture failed");
    return;
  }
  
  frameCount++;
  
  // Send frame header: FRAME:width:height:datasize\n
  Serial.printf("FRAME:%d:%d:%d\n", fb->width, fb->height, fb->len);
  
  // Send raw JPEG binary data
  Serial.write(fb->buf, fb->len);
  
  // Send newline terminator
  Serial.write('\n');
  
  esp_camera_fb_return(fb);
}

void setResolution(int framesize) {
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_framesize(s, (framesize_t)framesize);
    const char* names[] = {"QQVGA","QCIF","QVGA","CIF","VGA","SVGA","XGA","SXGA","UXGA"};
    int idx = framesize - 2;
    if (idx >= 0 && idx < 9) {
      Serial.printf("OK:Resolution set to %s (%d)\n", names[idx], framesize);
    } else {
      Serial.printf("OK:Resolution set to %d\n", framesize);
    }
  }
}

void setQuality(int quality) {
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_quality(s, quality);
    Serial.printf("OK:JPEG quality set to %d\n", quality);
  }
}

// ============== COMMAND HANDLER ==============
void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  
  if (cmd == "SNAP") {
    sendFrame();
  }
  else if (cmd == "STREAM") {
    streaming = true;
    Serial.println("OK:Streaming started");
  }
  else if (cmd == "STOP") {
    streaming = false;
    Serial.println("OK:Streaming stopped");
  }
  else if (cmd.startsWith("RES ")) {
    int res = cmd.substring(4).toInt();
    setResolution(res);
  }
  else if (cmd.startsWith("QUAL ")) {
    int q = cmd.substring(5).toInt();
    setQuality(q);
  }
  else if (cmd.startsWith("LED ")) {
    int state = cmd.substring(4).toInt();
    digitalWrite(LED_GPIO_NUM, state ? HIGH : LOW);
    Serial.printf("OK:LED %s\n", state ? "ON" : "OFF");
  }
  else if (cmd == "IMU") {
    readIMU();
    Serial.printf("IMU:%.4f:%.4f:%.4f:%.4f:%.4f:%.4f\n",
                  imuAccX, imuAccY, imuAccZ, imuGyrX, imuGyrY, imuGyrZ);
  }
  else if (cmd == "STATUS") {
    Serial.printf("STATUS:frames=%lu streaming=%d uptime=%lu\n",
                  frameCount, streaming, millis() / 1000);
  }
  else if (cmd == "HELP") {
    Serial.println("COMMANDS:");
    Serial.println("  SNAP      - Capture single frame");
    Serial.println("  STREAM    - Start continuous streaming");
    Serial.println("  STOP      - Stop streaming");
    Serial.println("  RES N     - Set resolution (5=QVGA,8=VGA,9=SVGA,10=XGA)");
    Serial.println("  QUAL N    - Set JPEG quality (0-63)");
    Serial.println("  LED 0/1   - Toggle LED");
    Serial.println("  IMU       - Read IMU data");
    Serial.println("  STATUS    - Show camera status");
    Serial.println("  HELP      - This help");
  }
  else if (cmd.length() > 0) {
    Serial.printf("ERR:Unknown command '%s'\n", cmd.c_str());
  }
}

// ============== SETUP & LOOP ==============
void setup() {
  Serial.begin(921600);
  Serial.setDebugOutput(true);
  delay(2000);
  
  Serial.println("\n================================");
  Serial.println("  Tank USB Camera v2.0");
  Serial.println("  DFRobot ESP32-S3 AI Camera");
  Serial.println("  USB Serial 921600 baud");
  Serial.println("================================\n");
  
  pinMode(LED_GPIO_NUM, OUTPUT);
  digitalWrite(LED_GPIO_NUM, LOW);
  
  initCamera();
  initIMU();
  
  Serial.println("OK:Ready. Send HELP for commands.");
}

String inputBuffer = "";

void loop() {
  // Read serial commands from Jetson
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        handleCommand(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += c;
    }
  }
  
  // Stream frames if enabled
  if (streaming) {
    unsigned long minFrameTime = 1000 / targetFps;
    if (millis() - lastFrameTime >= minFrameTime) {
      lastFrameTime = millis();
      sendFrame();
    }
  }
  
  delay(1);
}
