/*
 * Tank Eyes — Waveshare ESP32-S3 1.28" LCD Board
 * Drives the built-in GC9A01A round LCD as animated eyes
 * Receives commands from Jetson over USB serial (115200 baud)
 * Also reads onboard QMI8658 IMU for head tracking
 *
 * Commands from Jetson:
 *   {"cmd":"eye","gaze_x":0.0,"gaze_y":0.0,"open":1.0,"color":"#00ff88"}
 *   {"cmd":"blink"}
 *   {"cmd":"emotion","name":"happy"}
 *   {"cmd":"emotion","name":"sad"}
 *   {"cmd":"emotion","name":"angry"}
 *   {"cmd":"emotion","name":"neutral"}
 *   {"cmd":"emotion","name":"surprised"}
 *   {"cmd":"status"}
 *   {"cmd":"imu"}
 *   {"cmd":"test"}
 *
 * Waveshare ESP32-S3-LCD-1.28 pin mapping:
 *   LCD: SPI (internal) — DC=GPIO8, CS=GPIO9, CLK=GPIO10, MOSI=GPIO11, RST=GPIO12, BL=GPIO40
 *   IMU: I2C — SDA=GPIO6, SCL=GPIO7 (QMI8658)
 *   USB: CH343P — GPIO43(TX), GPIO44(RX)
 */

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include <ArduinoJson.h>

// ── Pin Definitions (Waveshare ESP32-S3-LCD-1.28) ──
#define LCD_DC    8
#define LCD_CS    9
#define LCD_CLK   10
#define LCD_MOSI  11
#define LCD_RST   12
#define LCD_BL    40
#define IMU_SDA   6
#define IMU_SCL   7

// ── Display ──
SPIClass hspi(HSPI);
Adafruit_GC9A01A tft(&hspi, LCD_CS, LCD_DC, LCD_RST);

// ── Colors ──
#define BLACK   0x0000
#define WHITE   0xFFFF
#define RED     0xF800
#define GREEN   0x07E0
#define BLUE    0x001F
#define CYAN    0x07FF
#define YELLOW  0xFFE0
#define ORANGE  0xFD20

// ── Eye State ──
struct EyeState {
  float gazeX;       // -1..+1
  float gazeY;       // -1..+1
  float openness;    // 0..1
  uint16_t irisColor;
  String emotion;
};

EyeState eye = {0.0, 0.0, 1.0, CYAN, "neutral"};

// ── Blink ──
bool blinkActive = false;
bool blinkClosing = true;
unsigned long nextBlinkMs = 3000;
unsigned long lastBlinkMs = 0;
float blinkOpen = 1.0;

// ── IMU ──
float imuAx = 0, imuAy = 0, imuAz = 0;
float imuGx = 0, imuGy = 0, imuGz = 0;

// ── Display Constants ──
const int CX = 120;
const int CY = 120;
const int RADIUS = 110;
const int IRIS_R = 45;

// ── Drawing ──
void drawEye(float gx, float gy, float open, uint16_t iris) {
  tft.fillScreen(BLACK);

  // Sclera (white of eye)
  tft.fillCircle(CX, CY, RADIUS, WHITE);

  // Iris + pupil — sized by openness
  int irisR = (int)(IRIS_R * open);
  if (irisR > 2) {
    int irisX = CX + (int)(gx * 30);
    int irisY = CY + (int)(gy * 30);

    // Outer iris
    tft.fillCircle(irisX, irisY, irisR, iris);
    // Pupil
    tft.fillCircle(irisX, irisY, irisR / 2, BLACK);
    // Highlight
    tft.fillCircle(irisX - irisR/4, irisY - irisR/4, irisR/5, WHITE);
  }

  // Eyelid (blink effect)
  if (open < 0.9) {
    int lidH = (int)((1.0 - open) * RADIUS * 2);
    tft.fillRect(0, CY - RADIUS, 240, lidH / 2, BLACK);
    tft.fillRect(0, CY + RADIUS - lidH / 2, 240, lidH / 2, BLACK);
  }
}

void drawEmotion(String emotion) {
  if (emotion == "happy") {
    eye.irisColor = GREEN;
    eye.openness = 1.0;
  } else if (emotion == "sad") {
    eye.irisColor = BLUE;
    eye.openness = 0.6;
  } else if (emotion == "angry") {
    eye.irisColor = RED;
    eye.openness = 0.8;
    eye.gazeY = 0.2;  // slightly downward
  } else if (emotion == "surprised") {
    eye.irisColor = YELLOW;
    eye.openness = 1.0;
    eye.gazeX = 0; eye.gazeY = 0;
  } else if (emotion == "neutral") {
    eye.irisColor = CYAN;
    eye.openness = 1.0;
    eye.gazeX = 0; eye.gazeY = 0;
  } else if (emotion == "sleepy") {
    eye.irisColor = 0x7BEF;  // dim cyan
    eye.openness = 0.3;
  }
  eye.emotion = emotion;
}

// ── IMU (QMI8658 via I2C) ──
void readIMU() {
  Wire.beginTransmission(0x6B);  // QMI8658 address
  Wire.write(0x35);  // Accel X out
  Wire.endTransmission(false);
  Wire.requestFrom(0x6B, 12, true);
  if (Wire.available() >= 12) {
    imuAx = (int16_t)(Wire.read() | Wire.read() << 8) / 16384.0;
    imuAy = (int16_t)(Wire.read() | Wire.read() << 8) / 16384.0;
    imuAz = (int16_t)(Wire.read() | Wire.read() << 8) / 16384.0;
    imuGx = (int16_t)(Wire.read() | Wire.read() << 8) / 131.0;
    imuGy = (int16_t)(Wire.read() | Wire.read() << 8) / 131.0;
    imuGz = (int16_t)(Wire.read() | Wire.read() << 8) / 131.0;
  }
}

// ── Serial Command Processing ──
void processCommand(String jsonStr) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, jsonStr);
  if (err) { Serial.println("{\"error\":\"parse_failed\"}"); return; }

  const char* cmd = doc["cmd"] | "";
  if (strcmp(cmd, "eye") == 0) {
    eye.gazeX = doc["gaze_x"] | 0.0f;
    eye.gazeY = doc["gaze_y"] | 0.0f;
    eye.openness = doc["open"] | 1.0f;
    if (doc.containsKey("color")) {
      const char* c = doc["color"];
      if (c[0] == '#') {
        long rgb = strtol(c + 1, NULL, 16);
        eye.irisColor = ((rgb >> 8) & 0xF800) | ((rgb >> 5) & 0x07E0) | ((rgb >> 3) & 0x001F);
      }
    }
    Serial.println("{\"ok\":true,\"cmd\":\"eye\"}");
  } else if (strcmp(cmd, "blink") == 0) {
    blinkActive = true;
    blinkClosing = true;
    Serial.println("{\"ok\":true,\"cmd\":\"blink\"}");
  } else if (strcmp(cmd, "emotion") == 0) {
    drawEmotion(doc["name"] | "neutral");
    Serial.printf("{\"ok\":true,\"emotion\":\"%s\"}\n", eye.emotion.c_str());
  } else if (strcmp(cmd, "imu") == 0) {
    readIMU();
    Serial.printf("{\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"gx\":%.1f,\"gy\":%.1f,\"gz\":%.1f}\n",
                  imuAx, imuAy, imuAz, imuGx, imuGy, imuGz);
  } else if (strcmp(cmd, "status") == 0) {
    Serial.printf("{\"board\":\"waveshare-esp32s3-lcd-1.28\",\"emotion\":\"%s\","
                  "\"gaze_x\":%.2f,\"gaze_y\":%.2f,\"open\":%.2f,\"uptime\":%lu}\n",
                  eye.emotion.c_str(), eye.gazeX, eye.gazeY, eye.openness, millis() / 1000);
  } else if (strcmp(cmd, "test") == 0) {
    // Cycle through colors
    tft.fillScreen(RED); delay(500);
    tft.fillScreen(GREEN); delay(500);
    tft.fillScreen(BLUE); delay(500);
    tft.fillScreen(BLACK);
    Serial.println("{\"ok\":true,\"cmd\":\"test\"}");
  } else {
    Serial.printf("{\"error\":\"unknown_cmd\",\"cmd\":\"%s\"}\n", cmd);
  }
}

// ── Setup ──
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== Tank Eyes — Waveshare ESP32-S3-LCD-1.28 ===");

  // Init I2C for IMU
  Wire.begin(IMU_SDA, IMU_SCL);
  Serial.println("I2C initialized (IMU: QMI8658)");

  // Init LCD
  pinMode(LCD_BL, OUTPUT);
  digitalWrite(LCD_BL, HIGH);
  hspi.begin(LCD_CLK, -1, LCD_MOSI, LCD_CS);
  tft.begin();
  tft.setRotation(0);
  tft.fillScreen(BLACK);
  Serial.println("LCD initialized (GC9A01A, 240x240)");

  // Draw initial eye
  drawEye(0, 0, 1.0, CYAN);
  Serial.println("Ready! Send JSON commands via serial.");
  Serial.println("Example: {\"cmd\":\"emotion\",\"name\":\"happy\"}");
}

// ── Loop ──
void loop() {
  // Process serial commands
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      processCommand(line);
    }
  }

  // Auto-blink
  if (millis() - lastBlinkMs > nextBlinkMs) {
    blinkActive = true;
    blinkClosing = true;
    lastBlinkMs = millis();
    nextBlinkMs = 2000 + random(4000);  // 2-6 seconds
  }

  // Blink animation
  if (blinkActive) {
    if (blinkClosing) {
      blinkOpen -= 0.15;
      if (blinkOpen <= 0.0) {
        blinkOpen = 0.0;
        blinkClosing = false;
      }
    } else {
      blinkOpen += 0.15;
      if (blinkOpen >= 1.0) {
        blinkOpen = 1.0;
        blinkActive = false;
      }
    }
  }

  // Draw eye
  drawEye(eye.gazeX, eye.gazeY, blinkActive ? blinkOpen : eye.openness, eye.irisColor);
  delay(33);  // ~30fps
}
