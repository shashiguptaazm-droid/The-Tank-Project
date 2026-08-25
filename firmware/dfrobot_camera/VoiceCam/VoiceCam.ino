/*
  VoiceCam.ino — DFRobot ESP32-S3 AI Camera (DFR1154), USB-only voice bridge.

  No WiFi. The Jetson talks to the camera over the USB-CDC serial port
  (/dev/ttyACM0, 115200). Line-based commands, binary payloads:

    SNAP\n            → "FRAME:<w>:<h>:<len>\n" + <len> JPEG bytes
    MIC <ms>\n        → "AUDIO:<len>\n" + last <ms> of mic as raw int16 PCM
                        (16 kHz / mono). <ms> clamped to 100..10000.
    SPEAK <len>\n     → read <len> raw int16 PCM bytes (16 kHz mono), play
                        through the MAX98357 speaker. Reply "OK\n".
    PING\n            → "PONG\n"
    STATUS\n          → "STATUS:<mic_seconds>:<playing>\n"

  Audio hardware (DFR1154 V1.1):
    - Mic:    I2S PDM microphone, CLK = GPIO38, DATA = GPIO39
    - Speaker: MAX98357 I2S class-D amp, BCLK = GPIO45, LRC = GPIO46, DOUT = GPIO42

  Arduino tool config:
    Board: ESP32S3 Dev Module | USB CDC on Boot: Enabled | CPU: 240 MHz
    Flash: 16 MB (QIO 80 MHz) | PSRAM: OPI PSRAM | Partition: Huge App (3MB No OTA)
    Requires ESP32 Arduino core 3.x (ESP_I2S.h) + the esp32-camera library.
*/

#include <esp_camera.h>
#include <ESP_I2S.h>
#include "driver/i2s_std.h"
#include "driver/i2s_types.h"

// ═══════════════════════════════ CAMERA PINS ═══════════════════════════════
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  5
#define Y9_GPIO_NUM    4
#define Y8_GPIO_NUM    6
#define Y7_GPIO_NUM    7
#define Y6_GPIO_NUM    14
#define Y5_GPIO_NUM    17
#define Y4_GPIO_NUM    21
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM    16
#define VSYNC_GPIO_NUM 1
#define HREF_GPIO_NUM  2
#define PCLK_GPIO_NUM  15
#define SIOD_GPIO_NUM  8
#define SIOC_GPIO_NUM  9
#define LED_GPIO_NUM   47

// ═══════════════════════════════ AUDIO PINS ════════════════════════════════
#define MIC_CLK_PIN  38   // PDM clock
#define MIC_DATA_PIN 39   // PDM data
#define SPK_BCLK     45   // MAX98357 bit clock
#define SPK_LRC      46   // MAX98357 word select
#define SPK_DOUT     42   // MAX98357 data

#define SAMPLE_RATE  16000
#define RING_SECONDS 10
#define RING_SIZE    (RING_SECONDS * SAMPLE_RATE * 2)   // 320000 bytes
#define RING_HALF    (RING_SIZE / 2)
#define ONBOARD_LED  3

I2SClass I2S;  // PDM RX (mic)

// ── Mic ring buffer (contiguous sliding window in PSRAM) ───────────────────
static uint8_t *ringBuf = nullptr;
static volatile size_t ringPos = 0;
static volatile bool micReady = false;
static volatile bool playing = false;

void ringAppend(const uint8_t *data, size_t n) {
  if (!ringBuf) return;
  if (ringPos + n > RING_SIZE) {
    memmove(ringBuf, ringBuf + RING_HALF, RING_HALF);
    ringPos -= RING_HALF;
  }
  memcpy(ringBuf + ringPos, data, n);
  ringPos += n;
  micReady = true;
}

// ── Mic capture task (core 0) ──────────────────────────────────────────────
void micTask(void *) {
  static uint8_t tmp[4096];
  while (true) {
    size_t avail = I2S.available();
    if (avail > 0) {
      size_t want = (avail > sizeof(tmp)) ? sizeof(tmp) : avail;
      size_t got = I2S.readBytes((char *)tmp, want);
      if (got > 0) ringAppend(tmp, got);
    }
    vTaskDelay(1);
  }
}

// ── Speaker (MAX98357, new I2S driver channel on I2S_NUM_1) ────────────────
static i2s_chan_handle_t tx_chan = NULL;

void initSpeaker() {
  i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
  if (i2s_new_channel(&chan_cfg, &tx_chan, NULL) != ESP_OK) {
    Serial.println("WARN: speaker channel init failed");
    return;
  }
  i2s_std_config_t std_cfg = {
      .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
      .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
      .gpio_cfg = {
          .mclk = I2S_GPIO_UNUSED,
          .bclk = (gpio_num_t)SPK_BCLK,
          .ws = (gpio_num_t)SPK_LRC,
          .dout = (gpio_num_t)SPK_DOUT,
          .din = I2S_GPIO_UNUSED,
          .invert_flags = {.mclk_inv = false, .bclk_inv = false, .ws_inv = false},
      },
  };
  i2s_channel_init_std_mode(tx_chan, &std_cfg);
  i2s_channel_enable(tx_chan);
}

void playPcm(const uint8_t *pcm, size_t len) {
  if (!tx_chan || len == 0) return;
  playing = true;
  digitalWrite(ONBOARD_LED, HIGH);
  size_t written = 0, idx = 0;
  while (idx < len) {
    size_t chunk = (len - idx > 4096) ? 4096 : (len - idx);
    i2s_channel_write(tx_chan, pcm + idx, chunk, &written, portMAX_DELAY);
    idx += chunk;
  }
  i2s_channel_disable(tx_chan);
  i2s_channel_enable(tx_chan);  // flush residual DMA
  digitalWrite(ONBOARD_LED, LOW);
  playing = false;
}

// ═══════════════════════════════ Camera ════════════════════════════════════
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
  if (config.pixel_format == PIXFORMAT_JPEG) {
    if (psramFound()) {
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  }
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }
  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL) {
    if (s->id.PID == OV3660_PID) {
      s->set_vflip(s, 1);
      s->set_brightness(s, 1);
      s->set_saturation(s, -2);
    }
    s->set_framesize(s, FRAMESIZE_QVGA);
  }
  Serial.println("Camera initialized successfully");
}

// ═══════════════════════════════ Serial helpers ════════════════════════════
// Read exactly n bytes from the USB-CDC serial with a timeout.
bool readNBytes(uint8_t *buf, size_t n, uint32_t timeoutMs) {
  size_t got = 0;
  uint32_t deadline = millis() + timeoutMs;
  while (got < n && millis() < deadline) {
    int r = Serial.read();
    if (r >= 0) {
      buf[got++] = (uint8_t)r;
      deadline = millis() + timeoutMs;  // reset timeout on activity
    }
  }
  return got == n;
}

// Read one line (until '\n'), returns length (without '\n').
size_t readLine(char *buf, size_t maxLen, uint32_t timeoutMs) {
  size_t n = 0;
  uint32_t deadline = millis() + timeoutMs;
  while (n < maxLen - 1 && millis() < deadline) {
    int r = Serial.read();
    if (r == '\n') break;
    if (r >= 0) {
      buf[n++] = (char)r;
      deadline = millis() + timeoutMs;
    }
  }
  buf[n] = 0;
  return n;
}

// ── Command handlers ───────────────────────────────────────────────────────
void handleSnap() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("FRAME:0:0:0");
    return;
  }
  Serial.printf("FRAME:%u:%u:%u\n", fb->width, fb->height, fb->len);
  size_t sent = 0;
  while (sent < fb->len) {
    sent += Serial.write(fb->buf + sent, fb->len - sent);
  }
  esp_camera_fb_return(fb);
}

void handleMic(const char *arg) {
  long ms = 1000;
  if (arg && *arg) ms = atol(arg);
  if (ms < 100) ms = 100;
  if (ms > 10000) ms = 10000;
  size_t want = (size_t)(ms * SAMPLE_RATE * 2 / 1000);
  if (!micReady || !ringBuf) {
    Serial.println("AUDIO:0");
    return;
  }
  size_t have = ringPos;
  size_t n = (want < have) ? want : have;
  size_t start = have - n;
  Serial.printf("AUDIO:%u\n", (unsigned)n);
  size_t sent = 0;
  while (sent < n) {
    sent += Serial.write(ringBuf + start + sent, n - sent);
  }
}

void handleSpeak(const char *arg) {
  long len = atol(arg);
  if (len <= 0 || len > 2 * 1024 * 1024) {
    Serial.println("ERR");
    return;
  }
  uint8_t *pcm = (uint8_t *)heap_caps_malloc((size_t)len, MALLOC_CAP_SPIRAM);
  if (!pcm) {
    Serial.println("ERR");
    return;
  }
  bool ok = readNBytes(pcm, (size_t)len, 30000);
  if (ok) {
    playPcm(pcm, (size_t)len);
    Serial.println("OK");
  } else {
    Serial.println("ERR");
  }
  free(pcm);
}

// ═══════════════════════════════ Setup / Loop ══════════════════════════════
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  delay(800);
  Serial.println("\n\n=== DFRobot ESP32-S3 VoiceCam (USB) ===\n");

  pinMode(ONBOARD_LED, OUTPUT);
  digitalWrite(ONBOARD_LED, LOW);

  ringBuf = (uint8_t *)heap_caps_malloc(RING_SIZE, MALLOC_CAP_SPIRAM);
  if (ringBuf) memset(ringBuf, 0, RING_SIZE);
  else Serial.println("WARN: mic ring buffer allocation failed");

  I2S.setPinsPdmRx(MIC_CLK_PIN, MIC_DATA_PIN);
  I2S.begin(I2S_MODE_PDM_RX, SAMPLE_RATE, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  xTaskCreatePinnedToCore(micTask, "mic", 4096, NULL, 1, NULL, 0);
  Serial.println("Mic task started");

  initSpeaker();
  Serial.println("Speaker ready");

  initCamera();

  Serial.println("READY");
}

void loop() {
  static char line[96];
  static uint8_t dummy;
  if (!Serial.available()) {
    delay(2);
    return;
  }
  size_t n = readLine(line, sizeof(line), 2000);
  if (n == 0) return;

  if (strncmp(line, "SNAP", 4) == 0) {
    handleSnap();
  } else if (strncmp(line, "MIC", 3) == 0) {
    const char *arg = (n > 4) ? line + 4 : "";
    while (*arg == ' ') arg++;
    handleMic(arg);
  } else if (strncmp(line, "SPEAK", 5) == 0) {
    const char *arg = (n > 6) ? line + 6 : "";
    while (*arg == ' ') arg++;
    handleSpeak(arg);
  } else if (strncmp(line, "PING", 4) == 0) {
    Serial.println("PONG");
  } else if (strncmp(line, "STATUS", 6) == 0) {
    Serial.printf("STATUS:%u:%s\n",
                  (unsigned)(ringPos / (SAMPLE_RATE * 2)),
                  playing ? "playing" : "idle");
  } else {
    // Drain any unexpected partial payload so the stream stays in sync.
    while (Serial.available()) {
      if (Serial.read() == '\n') break;
    }
    Serial.println("ERR");
  }
  (void)dummy;
}
