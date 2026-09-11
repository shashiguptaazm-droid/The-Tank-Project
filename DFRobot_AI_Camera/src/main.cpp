#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_camera.h"

// --- WiFi Settings ---
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define TARGET_IP "255.255.255.255" // Broadcast
#define TARGET_PORT 12345

// --- DFR1154 Camera Pins ---
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     5
#define SIOD_GPIO_NUM     8
#define SIOC_GPIO_NUM     9

#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       18
#define Y7_GPIO_NUM       21
#define Y6_GPIO_NUM       17
#define Y5_GPIO_NUM       14
#define Y4_GPIO_NUM       7
#define Y3_GPIO_NUM       6
#define Y2_GPIO_NUM       4
#define VSYNC_GPIO_NUM    1
#define HREF_GPIO_NUM     2
#define PCLK_GPIO_NUM     15

WiFiUDP udp;
unsigned long last_send_time = 0;
const unsigned long SEND_INTERVAL_MS = 50; // Send coordinates 20 times per second

void setup() {
  delay(2000);
  Serial.begin(115200);
  unsigned long start_time = millis();
  while (!Serial && (millis() - start_time < 2000)) {
    delay(100);
  }
  
  Serial.println("Booting DFRobot AI Camera...");

  // --- WiFi Setup ---
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Connecting to WiFi: %s ", WIFI_SSID);
  unsigned long wifi_start = millis();
  bool wifi_connected = true;
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
    if (millis() - wifi_start > 6000) {
      Serial.println("\nWiFi timeout. Running in Serial USB mode only.");
      wifi_connected = false;
      break;
    }
  }
  if (wifi_connected) {
    Serial.println("\nWiFi Connected!");
    Serial.print("Camera IP: ");
    Serial.println(WiFi.localIP());
  }

  // --- Camera Config ---
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
  config.frame_size = FRAMESIZE_QQVGA; // 160x120 pixels for high-speed tracking
  config.pixel_format = PIXFORMAT_GRAYSCALE; // Grayscale is easiest for tracking brightness/centroids
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  // Initialize Camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    while (1) { delay(100); }
  }
  Serial.println("Camera initialized successfully.");
}

void loop() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    delay(100);
    return;
  }

  // --- Centroid of Brightest Region Algorithm ---
  int sum_x = 0;
  int sum_y = 0;
  int count = 0;
  int max_brightness = 0;
  int min_brightness = 255;
  int len = fb->width * fb->height;

  // 1. Find the min and max brightness in the frame
  for (int i = 0; i < len; i++) {
    if (fb->buf[i] > max_brightness) max_brightness = fb->buf[i];
    if (fb->buf[i] < min_brightness) min_brightness = fb->buf[i];
  }

  // 2. Compute centroid of the brightest pixels (top 15% threshold)
  int threshold = max_brightness - (max_brightness - min_brightness) / 6;
  
  // Ensure we have some minimum contrast to avoid tracking noise
  if (max_brightness - min_brightness > 25) {
    for (int y = 0; y < fb->height; y++) {
      for (int x = 0; x < fb->width; x++) {
        int idx = y * fb->width + x;
        if (fb->buf[idx] >= threshold) {
          sum_x += x;
          sum_y += y;
          count++;
        }
      }
    }
  }

  // Release frame buffer back to driver
  esp_camera_fb_return(fb);

  if (count > 0 && millis() - last_send_time >= SEND_INTERVAL_MS) {
    last_send_time = millis();
    
    // Calculate normalized target coordinates (-1.0 to 1.0)
    // Map x (0 to width) and y (0 to height)
    float raw_x = (float)(sum_x / count) / 160.0f; // 0.0 to 1.0
    float raw_y = (float)(sum_y / count) / 120.0f; // 0.0 to 1.0
    
    // Translate coordinates: camera frame to robot eyes coordinate system
    // We constrain to range -1.0 to 1.0
    float final_x = constrain((raw_x - 0.5f) * 2.0f, -1.0f, 1.0f);
    float final_y = constrain((raw_y - 0.5f) * 2.0f, -1.0f, 1.0f);

    // Format coordinates payload
    String serial_payload = "X:" + String(final_x, 3) + ",Y:" + String(final_y, 3);
    String udp_payload = String(final_x, 3) + "," + String(final_y, 3);

    // Send over Serial USB
    Serial.println(serial_payload);

    // Send over Wi-Fi UDP if connected
    if (WiFi.status() == WL_CONNECTED) {
      udp.beginPacket(TARGET_IP, TARGET_PORT);
      udp.write((const uint8_t*)udp_payload.c_str(), udp_payload.length());
      udp.endPacket();
    }
  }
}
