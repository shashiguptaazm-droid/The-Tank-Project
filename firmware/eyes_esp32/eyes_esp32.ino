// The Tank Project — AI eyes
// ESP32-S3 drives two Waveshare 1.28-inch round GC9A01 LCDs (240x240,
// SPI), one per eye, and receives high-level commands from the Raspberry
// Pi 5 over UART2 in line-delimited JSON.
//
// Wiring (ESP32-S3 DevKitC-1 reference):
//   SCK  -> GPIO12    MOSI -> GPIO11     DC -> GPIO17     RST -> GPIO16
//   CS-left  -> GPIO7   CS-right -> GPIO15
//   BL-left  -> GPIO6   BL-right -> GPIO5
//   UART2 RX (Pi TX -> ESP RX) -> GPIO18
//   UART2 TX (Pi RX -> ESP TX) -> GPIO8
//
// Arduino IDE library requirements (Board: ESP32S3 Dev Module):
//   - Adafruit_GC9A101
//   - ArduinoJson
//
// Build: open in Arduino IDE 2.x, choose board ESP32S3 Dev Module,
// flash over USB. The ESP32-S3 will start advertising its two eyes
// in 'neutral' expression and an automatic blink every 2-6 seconds.

#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GC9A101.h>
#include <ArduinoJson.h>

// ---------------- Pin assignments ----------------
constexpr int PIN_MOSI      = 11;
constexpr int PIN_SCK       = 12;
constexpr int PIN_DC        = 17;
constexpr int PIN_RST       = 16;
constexpr int PIN_CS_LEFT   = 7;
constexpr int PIN_CS_RIGHT  = 15;
constexpr int PIN_BL_LEFT   = 6;
constexpr int PIN_BL_RIGHT  = 5;
constexpr int PIN_UART_RX   = 18;
constexpr int PIN_UART_TX   = 8;
constexpr long UART_BAUD    = 115200;
constexpr int  FRAME_MS     = 33;        // ~30 fps
constexpr int  RING_RADIUS  = 110;
constexpr int  DISPLAY_W    = 240;
constexpr int  DISPLAY_H    = 240;

// ---------------- SPI bus + displays ----------------
SPIClass hspi(HSPI);
Adafruit_GC9A101 tftLeft (&hspi, PIN_CS_LEFT,  PIN_DC, PIN_RST);
Adafruit_GC9A101 tftRight(&hspi, PIN_CS_RIGHT, PIN_DC, PIN_RST);

// ---------------- Eye state ----------------
struct EyeTarget {
  float   gazeX;            // -1..+1
  float   gazeY;            // -1..+1  (up is negative)
  float   openness;         // 0..1
  uint16_t irisColor;       // RGB565
};

EyeTarget target = {0.0f, 0.0f, 1.0f, 0x44A4};

float g_gazeX = 0.0f, g_gazeY = 0.0f, g_open = 1.0f;

bool blinkInProgress = false;
bool blinkClosing    = true;
unsigned long nextBlinkMs   = 2000;
unsigned long lastHeartbeat =   0;

// ---------------- Drawing ----------------
static void drawEye(Adafruit_GC9A101& tft,
                    float gx, float gy,
                    float open, uint16_t iris) {
  const int cx = DISPLAY_W / 2;
  const int cy = DISPLAY_H / 2;

  // Black border (round display only fills a circle)
  tft.fillScreen(BLACK);

  // Sclera
  tft.fillCircle(cx, cy, RING_RADIUS, 0xEF7D);   // off-white

  // Iris + pupil — sized by openness so a blink literally closes the iris
  const int irisR = (int)(45.0f * open);
  if (irisR > 2) {
    const int ix = cx + (int)(gx * 35.0f);
    const int iy = cy - (int)(gy * 30.0f);
    tft.fillCircle(ix, iy, irisR, iris);
    const int pupR = (int)(20.0f * open);
    if (pupR > 2) {
      tft.fillCircle(ix, iy, pupR, BLACK);
    }
    if (open > 0.6f) {
      tft.fillCircle(ix - irisR / 3, iy - irisR / 3,
                     max(2, irisR / 5), WHITE);
    }
  }

  // Eyelid (closed-eye look for blush arcs; sym across full expression)
  if (open < 2.0f / 3.0f) {
    // top lash hint
    tft.fillRect(cx - RING_RADIUS, cy - RING_RADIUS, 2 * RING_RADIUS, 3, BLACK);
  }
}

// ---------------- Command parsing ----------------
static uint16_t colorForExpr(const char* e) {
  if (!strcmp(e, "happy"))   return 0xFD20;   // amber
  if (!strcmp(e, "sad"))     return 0x3F4F;   // deep blue
  if (!strcmp(e, "angry"))   return 0xC800;   // red
  if (!strcmp(e, "scared"))  return 0xFFFF;   // white
  return 0x44A4;                              // neutral hazel
}

static void onCmdLine(const String& line) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, line)) return;

  if (doc.containsKey("gaze")) {
    JsonArray g = doc["gaze"].as<JsonArray>();
    if (g.size() == 2) {
      target.gazeX = g[0].as<float>();
      target.gazeY = g[1].as<float>();
    }
  }
  if (doc.containsKey("open")) {
    target.openness = doc["open"].as<float>();
    if (target.openness < 0.0f) target.openness = 0.0f;
    if (target.openness > 1.0f) target.openness = 1.0f;
  }
  if (doc.containsKey("iris")) {
    target.irisColor = doc["iris"].as<uint16_t>();
  }
  if (doc.containsKey("expr")) {
    target.irisColor = colorForExpr(doc["expr"].as<const char*>());
  }
  if (doc.containsKey("blink") && doc["blink"].as<bool>()) {
    blinkInProgress = true;
    blinkClosing    = true;
  }
}

static void drainUart() {
  while (Serial2.available()) {
    String line = Serial2.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) onCmdLine(line);
  }
}

// ---------------- Setup ----------------
void setup() {
  Serial.begin(115200);                       // logs over USB CDC

  Serial2.begin(UART_BAUD, SERIAL_8N1,
                PIN_UART_RX, PIN_UART_TX);    // Pi5 ↔ ESP32-S3 UART2

  hspi.begin(PIN_SCK, -1, PIN_MOSI, -1);

  tftLeft.begin(40000000);
  tftRight.begin(40000000);

  tftLeft.setRotation(0);
  tftRight.setRotation(0);

  pinMode(PIN_BL_LEFT,  OUTPUT); digitalWrite(PIN_BL_LEFT,  HIGH);
  pinMode(PIN_BL_RIGHT, OUTPUT); digitalWrite(PIN_BL_RIGHT, HIGH);

  drawEye(tftLeft,  0.0f, 0.0f, 1.0f, target.irisColor);
  drawEye(tftRight, 0.0f, 0.0f, 1.0f, target.irisColor);
}

// ---------------- Loop ----------------
void loop() {
  drainUart();

  const unsigned long now = millis();

  // Auto-blink every 2-6 seconds
  if (!blinkInProgress && (long)(now - nextBlinkMs) > 0) {
    blinkInProgress = true;
    blinkClosing = true;
    nextBlinkMs = now + random(2000, 6000);
  }

  // Easing toward the target state
  if (blinkInProgress) {
    if (blinkClosing) {
      g_open -= 0.10f;
      if (g_open < 0.06f) { g_open = 0.06f; blinkClosing = false; }
    } else {
      g_open += 0.10f;
      if (g_open >= target.openness) {
        g_open = target.openness;
        blinkInProgress = false;
      }
    }
  } else {
    g_open   += (target.openness - g_open)   * 0.20f;
  }
  g_gazeX  += (target.gazeX  - g_gazeX) * 0.25f;
  g_gazeY  += (target.gazeY  - g_gazeY) * 0.25f;

  drawEye(tftLeft,  g_gazeX, g_gazeY, g_open, target.irisColor);
  drawEye(tftRight, g_gazeX, g_gazeY, g_open, target.irisColor);

  // Heartbeat back to Pi every 250 ms
  if (now - lastHeartbeat > 250) {
    Serial2.printf("{\"hb\":%lu,\"open\":%.2f}\n", now, g_open);
    lastHeartbeat = now;
  }

  delay(FRAME_MS);
}
