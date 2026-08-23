/*
 * ESP32-S3 CAM — USB Serial Camera Firmware v2
 * Auto-detects camera sensor across common pin configurations.
 *
 * Tries multiple I2C pin pairs to find the camera sensor.
 * Once found, captures JPEG frames via USB serial SNAP command.
 *
 * Protocol (921600 baud):
 *   HOST → "SNAP\n", "STATUS\n", "LED 1\n", "LED 0\n"
 *   CAM  → "FRAME:<w>:<h>:<size>\n" + JPEG bytes, "OK:...\n", "ERR:...\n"
 */

#include "esp_camera.h"
#include <Wire.h>
#include "esp_heap_caps.h"

#define LED_FLASH_PIN  4

// ── TRY THESE PIN CONFIGS (I2C pairs most likely to work) ──
struct CamPins {
  int xclk, pclk, vsync, href;
  int sda, scl;
  int y2, y3, y4, y5, y6, y7, y8, y9;
  int pwdn, reset;
};

static const CamPins CONFIGS[] = {
  // Config 0: DFRobot / ESP32-S3 CAM (GPIO8/9 I2C)
  {5, 15, 1, 2,  8, 9,   16,18,21,17,14,7,6,4,  -1,-1},
  // Config 1: Generic ESP32-S3 (GPIO4/5 I2C)  
  {15, 13, 6, 7,  4, 5,   14,47,13,21,48,11,12,16,  -1,-1},
  // Config 2: AI-Thinker ESP32-S3 style
  {10, 13, 38, 47, 40, 39,  12,11,15,16,17,18,14,48, -1,-1},
};

static int found_config = -1;

void setup_camera(int idx) {
  const CamPins &p = CONFIGS[idx];
  
  camera_config_t cfg = {};
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer = LEDC_TIMER_0;
  cfg.pin_d0 = p.y2;   cfg.pin_d1 = p.y3;
  cfg.pin_d2 = p.y4;   cfg.pin_d3 = p.y5;
  cfg.pin_d4 = p.y6;   cfg.pin_d5 = p.y7;
  cfg.pin_d6 = p.y8;   cfg.pin_d7 = p.y9;
  cfg.pin_xclk = p.xclk;     cfg.pin_pclk = p.pclk;
  cfg.pin_vsync = p.vsync;   cfg.pin_href = p.href;
  cfg.pin_sccb_sda = p.sda;  cfg.pin_sccb_scl = p.scl;
  cfg.pin_pwdn = p.pwdn;     cfg.pin_reset = p.reset;
  cfg.xclk_freq_hz = 20000000;
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.frame_size = FRAMESIZE_QVGA;   // 320x240
  cfg.jpeg_quality = 12;
  cfg.fb_count = 2;                   // need 2 buffers for GRAB_WHEN_EMPTY
  cfg.fb_location = CAMERA_FB_IN_DRAM;   // try DRAM if PSRAM not available
  cfg.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  esp_camera_deinit();
  esp_err_t err = esp_camera_init(&cfg);
  if (err == ESP_OK) {
    found_config = idx;
    sensor_t *s = esp_camera_sensor_get();
    Serial.printf("OK: Camera ready (%s, %dx%d, pins=%d, psram=%d)\n",
      s->id.PID == OV2640_PID ? "OV2640" : 
      s->id.PID == OV3660_PID ? "OV3660" : "unknown",
      resolution[s->status.framesize].width,
      resolution[s->status.framesize].height, idx,
      heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
  } else {
    Serial.printf("DBG: Config %d failed: 0x%x\n", idx, err);
  }
}

void setup() {
  Serial.begin(921600);
  while (!Serial) delay(10);
  delay(500);
  pinMode(LED_FLASH_PIN, OUTPUT);
  digitalWrite(LED_FLASH_PIN, LOW);
  
  // Try each pin config
  for (int i = 0; i < 3; i++) {
    setup_camera(i);
    if (found_config >= 0) break;
    delay(100);
  }
  
  if (found_config < 0) {
    Serial.println("ERR: No camera found — tried 3 pin configs");
  }
}

void loop() {
  if (!Serial.available()) { delay(10); return; }
  
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  
  if (cmd == "SNAP") {
    if (found_config < 0) {
      Serial.println("ERR: No camera");
      return;
    }
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.printf("ERR: Capture failed (psram_free=%d)\n",
        heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
      return;
    }
    Serial.printf("FRAME:%d:%d:%d\n", fb->width, fb->height, fb->len);
    Serial.write(fb->buf, fb->len);
    Serial.write('\n');
    esp_camera_fb_return(fb);
  }
  else if (cmd == "STATUS") {
    if (found_config < 0) {
      Serial.println("ERR: No camera found");
    } else {
      sensor_t *s = esp_camera_sensor_get();
      Serial.printf("OK: %s %dx%d config=%d\n",
        s->id.PID == OV2640_PID ? "OV2640" : 
        s->id.PID == OV3660_PID ? "OV3660" : "?",
        resolution[s->status.framesize].width,
        resolution[s->status.framesize].height, found_config);
    }
  }
  else if (cmd == "RESCAN") {
    found_config = -1;
    for (int i = 0; i < 3; i++) {
      setup_camera(i);
      if (found_config >= 0) break;
    }
  }
  else if (cmd.startsWith("LED ")) {
    digitalWrite(LED_FLASH_PIN, cmd.substring(4).toInt() ? HIGH : LOW);
    Serial.println("OK");
  }
  else if (cmd == "LIST") {
    Serial.println("Commands: SNAP STATUS LED RESCAN LIST");
  }
  else {
    Serial.printf("ERR: Unknown: %s\n", cmd.c_str());
  }
}