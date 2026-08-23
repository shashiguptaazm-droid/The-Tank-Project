/*
 * ESP32-S3 CAM v6 — Keyestudio MB0184 / N16R8 pinout
 *
 * Proven pin mapping (from Keyestudio docs):
 *   SIOD=4, SIOC=5, VSYNC=6, HREF=7, XCLK=15, PCLK=13
 *   D0(Y2)=11, D1(Y3)=9, D2(Y4)=8, D3(Y5)=10, D4(Y6)=12, D5(Y7)=18, D6(Y8)=17, D7(Y9)=16
 *   PWDN=-1, RESET=-1
 *
 * Protocol (921600 baud):
 *   HOST → "SNAP\n", "STATUS\n"
 *   CAM  → "FRAME:<w>:<h>:<size>\n" + JPEG bytes + \n
 */
#include "esp_camera.h"
#include "esp_heap_caps.h"

void setup() {
  Serial.begin(921600);
  while(!Serial) delay(10);
  delay(500);

  Serial.printf("PSRAM: %s (%d free)\n",
    psramFound() ? "OK" : "NONE",
    psramFound() ? heap_caps_get_free_size(MALLOC_CAP_SPIRAM) : -1);

  camera_config_t cfg = {};
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer = LEDC_TIMER_0;
  // Keyestudio MB0184 pinout
  cfg.pin_d0  = 11;  // Y2
  cfg.pin_d1  = 9;   // Y3
  cfg.pin_d2  = 8;   // Y4
  cfg.pin_d3  = 10;  // Y5
  cfg.pin_d4  = 12;  // Y6
  cfg.pin_d5  = 18;  // Y7
  cfg.pin_d6  = 17;  // Y8
  cfg.pin_d7  = 16;  // Y9
  cfg.pin_xclk     = 15;
  cfg.pin_pclk     = 13;
  cfg.pin_vsync    = 6;
  cfg.pin_href     = 7;
  cfg.pin_sccb_sda = 4;
  cfg.pin_sccb_scl = 5;
  cfg.pin_pwdn     = -1;
  cfg.pin_reset    = -1;
  cfg.xclk_freq_hz  = 20000000;
  cfg.pixel_format  = PIXFORMAT_JPEG;
  cfg.frame_size    = FRAMESIZE_QVGA;
  cfg.jpeg_quality  = 12;
  cfg.fb_count      = 1;
  cfg.fb_location   = CAMERA_FB_IN_PSRAM;
  cfg.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&cfg);
  if (err != ESP_OK) {
    Serial.printf("ERR: camera_init=0x%x\n", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  Serial.printf("OK: %s %dx%d\n",
    s->id.PID == OV5640_PID ? "OV5640" : s->id.PID == OV3660_PID ? "OV3660" : "OV2640",
    resolution[s->status.framesize].width,
    resolution[s->status.framesize].height);

  // Warm up with dummy grabs
  for(int i = 0; i < 4; i++) {
    camera_fb_t *fb = esp_camera_fb_get();
    if(fb) { esp_camera_fb_return(fb); Serial.print("."); }
    delay(50);
  }
  Serial.println();
}

void loop() {
  if(!Serial.available()) { delay(10); return; }
  String cmd = Serial.readStringUntil('\n'); cmd.trim();

  if(cmd == "SNAP") {
    camera_fb_t *fb = esp_camera_fb_get();
    if(!fb) {
      Serial.printf("ERR: fb_get=null psram=%d\n", heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
      return;
    }
    Serial.printf("FRAME:%d:%d:%d\n", fb->width, fb->height, fb->len);
    Serial.write(fb->buf, fb->len);
    Serial.write('\n');
    esp_camera_fb_return(fb);
  }
  else if(cmd == "STATUS") {
    sensor_t *s = esp_camera_sensor_get();
    Serial.printf("OK: %s %dx%d psram=%d\n",
      s->id.PID == OV5640_PID ? "OV5640" : s->id.PID == OV3660_PID ? "OV3660" : "OV2640",
      resolution[s->status.framesize].width,
      resolution[s->status.framesize].height,
      heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
  }
  else if(cmd == "LIST") Serial.println("SNAP STATUS LIST");
  else Serial.printf("ERR:? %s\n", cmd.c_str());
}
