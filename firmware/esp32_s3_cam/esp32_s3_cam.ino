/*
 * ESP32-S3 CAM — USB Serial Camera Firmware
 * For Arduino UNO Q perception node
 *
 * Captures JPEG frames from OV2640/OV3660 and streams over USB serial.
 * No WiFi needed — direct USB connection to UNO Q.
 *
 * Protocol (921600 baud):
 *   Host → Camera:  "SNAP\n"     = capture single frame
 *   Host → Camera:  "STATUS\n"   = sensor info
 *   Host → Camera:  "LED 1\n"    = flash on
 *   Host → Camera:  "LED 0\n"    = flash off
 *
 *   Camera → Host:  "FRAME:<w>:<h>:<size>\n" + <jpeg_bytes>
 *   Camera → Host:  "OK: <msg>\n"
 *   Camera → Host:  "ERR: <msg>\n"
 *
 * Arduino IDE Settings:
 *   Board: ESP32S3 Dev Module
 *   USB CDC On Boot: Enabled
 *   USB Mode: Hardware CDC and JTAG
 *   PSRAM: OPI PSRAM
 *   Flash Size: 16MB
 *   Partition Scheme: Huge App (3MB No OTA)
 */

#include "esp_camera.h"

// ── ESP32-S3 CAM PIN CONFIG (AI-Thinker compatible) ──
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     10
#define SIOD_GPIO_NUM     40
#define SIOC_GPIO_NUM     39

#define Y9_GPIO_NUM       48
#define Y8_GPIO_NUM       11
#define Y7_GPIO_NUM       12
#define Y6_GPIO_NUM       14
#define Y5_GPIO_NUM       16
#define Y4_GPIO_NUM       18
#define Y3_GPIO_NUM       17
#define Y2_GPIO_NUM       15
#define VSYNC_GPIO_NUM    38
#define HREF_GPIO_NUM     47
#define PCLK_GPIO_NUM     13

#define LED_FLASH_PIN     4      // onboard LED/flash

static camera_config_t camera_config = {
    .pin_pwdn       = PWDN_GPIO_NUM,
    .pin_reset      = RESET_GPIO_NUM,
    .pin_xclk       = XCLK_GPIO_NUM,
    .pin_sccb_sda   = SIOD_GPIO_NUM,
    .pin_sccb_scl   = SIOC_GPIO_NUM,

    .pin_d7         = Y9_GPIO_NUM,
    .pin_d6         = Y8_GPIO_NUM,
    .pin_d5         = Y7_GPIO_NUM,
    .pin_d4         = Y6_GPIO_NUM,
    .pin_d3         = Y5_GPIO_NUM,
    .pin_d2         = Y4_GPIO_NUM,
    .pin_d1         = Y3_GPIO_NUM,
    .pin_d0         = Y2_GPIO_NUM,
    .pin_vsync      = VSYNC_GPIO_NUM,
    .pin_href       = HREF_GPIO_NUM,
    .pin_pclk       = PCLK_GPIO_NUM,

    .xclk_freq_hz   = 20000000,
    .ledc_timer     = LEDC_TIMER_0,
    .ledc_channel   = LEDC_CHANNEL_0,

    .pixel_format   = PIXFORMAT_JPEG,
    .frame_size     = FRAMESIZE_VGA,     // 640x480
    .jpeg_quality   = 12,                // 0-63, lower = better
    .fb_count       = 2,
    .grab_mode      = CAMERA_GRAB_WHEN_EMPTY,
};

void setup() {
    Serial.begin(921600);
    while (!Serial) delay(10);
    delay(500);

    // Init camera
    esp_err_t err = esp_camera_init(&camera_config);
    if (err != ESP_OK) {
        Serial.printf("ERR: Camera init failed: 0x%x\n", err);
        return;
    }

    // Init LED
    pinMode(LED_FLASH_PIN, OUTPUT);
    digitalWrite(LED_FLASH_PIN, LOW);

    // Get sensor info
    sensor_t *s = esp_camera_sensor_get();
    Serial.printf("OK: Camera ready — %s, %dx%d\n",
                  s->id.PID == OV2640_PID ? "OV2640" :
                  s->id.PID == OV3660_PID ? "OV3660" : "unknown",
                  resolution[s->status.framesize].width,
                  resolution[s->status.framesize].height);
}

void loop() {
    if (!Serial.available()) {
        delay(10);
        return;
    }

    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "SNAP") {
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("ERR: Frame capture failed");
            return;
        }

        Serial.printf("FRAME:%d:%d:%d\n", fb->width, fb->height, fb->len);
        Serial.write(fb->buf, fb->len);
        Serial.write('\n');
        esp_camera_fb_return(fb);
    }
    else if (cmd == "STATUS") {
        sensor_t *s = esp_camera_sensor_get();
        Serial.printf("OK: %s %dx%d quality=%d\n",
                      s->id.PID == OV2640_PID ? "OV2640" :
                      s->id.PID == OV3660_PID ? "OV3660" : "unknown",
                      resolution[s->status.framesize].width,
                      resolution[s->status.framesize].height,
                      s->status.quality);
    }
    else if (cmd.startsWith("LED ")) {
        int val = cmd.substring(4).toInt();
        digitalWrite(LED_FLASH_PIN, val ? HIGH : LOW);
        Serial.printf("OK: LED %s\n", val ? "ON" : "OFF");
    }
    else {
        Serial.printf("ERR: Unknown command: %s\n", cmd.c_str());
    }
}