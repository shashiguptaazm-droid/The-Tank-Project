/**
 * @file Dual_Display_Firmware.ino
 * @author Intellar (https://github.com/intellar)
 * @brief Main firmware for the dual-display animated eye project.
 * @version 1.1
 *
 * @copyright Copyright (c) 2024
 *
 * @license See LICENSE.md for details.
 *
 */

#include <Arduino.h>
#include "config.h"
// #include "esp32-hal-log.h" // Désactivé pour le débogage
#include "LittleFS.h"
// --- Bibliothèques désactivées pour le débogage ---
#include "drawing_tools.h"
#include "eye_logic.h"
#include "tof_sensor.h"

#if ENABLE_WIFI
#include <WiFi.h>
#include <WiFiUdp.h>
#endif

// --- FPS Counter Variables ---
// --- LED Blink Configuration ---
#define LED_PIN 48 // Broche de la LED intégrée. Changez-la si nécessaire (ex: LED_BUILTIN, 2, etc.)

// --- Battery Monitoring ---
#define BATT_ADC_PIN 4 // Broche ADC pour la lecture de la tension de la batterie


// --- FPS Counter Variables ---
static unsigned long last_fps_time = 0;
static int frame_count = 0;
static float current_fps = 0.0f;

#if ENABLE_WIFI
static WiFiUDP udp;
static char packetBuffer[255];
#endif

// Coordinated/AI Camera Gaze Target state
static TofTarget camera_target = {0.0f, 0.0f, 0, false, -1, -1, 0};
static unsigned long last_camera_update_time = 0;

void handle_serial_input() {
  while (Serial.available() > 0) {
    static String inputString = "";
    char inChar = (char)Serial.read();
    if (inChar == '\n' || inChar == '\r') {
      if (inputString.length() > 0) {
        inputString.trim();
        float x = 0.0f;
        float y = 0.0f;
        bool parse_success = false;

        if (inputString.startsWith("DFROBOT:") || inputString.startsWith("dfrobot:")) {
          int commaIdx = inputString.indexOf(':', 8);
          if (commaIdx != -1) {
            String xStr = inputString.substring(8, commaIdx);
            int yLabelIdx = inputString.indexOf(':', commaIdx);
            if (yLabelIdx != -1) {
              String yStr = inputString.substring(yLabelIdx + 1);
              x = xStr.toFloat();
              y = yStr.toFloat();
              parse_success = true;
            }
          }
        } else if (inputString.startsWith("X:") || inputString.startsWith("x:")) {
          int commaIdx = inputString.indexOf(',');
          if (commaIdx != -1) {
            String xStr = inputString.substring(2, commaIdx);
            int yLabelIdx = inputString.indexOf(':', commaIdx);
            if (yLabelIdx != -1) {
              String yStr = inputString.substring(yLabelIdx + 1);
              x = xStr.toFloat();
              y = yStr.toFloat();
              parse_success = true;
            }
          }
        } else {
          int commaIdx = inputString.indexOf(',');
          if (commaIdx != -1) {
            String xStr = inputString.substring(0, commaIdx);
            String yStr = inputString.substring(commaIdx + 1);
            x = xStr.toFloat();
            y = yStr.toFloat();
            parse_success = true;
          }
        }

        if (parse_success) {
          camera_target.x = constrain(x, -1.0f, 1.0f);
          camera_target.y = constrain(y, -1.0f, 1.0f);
          camera_target.is_valid = true;
          last_camera_update_time = millis();
        }
        inputString = "";
      }
    } else {
      inputString += inChar;
    }
  }
}

void handle_udp_input() {
  #if ENABLE_WIFI
    int packetSize = udp.parsePacket();
    if (packetSize) {
      int len = udp.read(packetBuffer, 255);
      if (len > 0) {
        packetBuffer[len] = 0;
        String msg = String(packetBuffer);
        msg.trim();
        
        float x = 0.0f;
        float y = 0.0f;
        bool parse_success = false;

        int commaIdx = msg.indexOf(',');
        if (commaIdx != -1) {
          String xStr = msg.substring(0, commaIdx);
          String yStr = msg.substring(commaIdx + 1);
          x = xStr.toFloat();
          y = yStr.toFloat();
          parse_success = true;
        }

        if (parse_success) {
          camera_target.x = constrain(x, -1.0f, 1.0f);
          camera_target.y = constrain(y, -1.0f, 1.0f);
          camera_target.is_valid = true;
          last_camera_update_time = millis();
        }
      }
    }
  #endif
}

// --- Debugging ---

/**
 * @brief Lit la tension de la batterie et la retourne en pourcentage.
 * @return Le pourcentage de batterie restant (0-100).
 */
int get_battery_percentage() {
  // Lit la valeur brute de l'ADC (0-4095)
  uint32_t raw_value = analogRead(BATT_ADC_PIN);

  // Convertit la valeur brute en millivolts à la broche ADC
  // La référence de tension est d'environ 3.3V (3300mV) pour une lecture max de 4095
  float adc_voltage = (raw_value / 4095.0) * 3300.0;

  // La tension de la batterie est le double de la tension lue à cause du diviseur de tension
  float battery_voltage = adc_voltage * 2.0;

  // Mappe la tension de la batterie (3.2V-4.2V) à un pourcentage (0-100%)
  // map(valeur, min_entree, max_entree, min_sortie, max_sortie)
  int percentage = map(battery_voltage, 3200, 4200, 0, 100);
  return constrain(percentage, 0, 100); // S'assure que la valeur reste entre 0 et 100
}
/**
 * @brief Initializes all subsystems.
 */
void setup() {
  // Ajout d'un délai fixe pour garantir que le moniteur série a le temps de se connecter.
  delay(2000);

  Serial.begin(115200);
  // Attend que le port série soit connecté. Indispensable pour l'ESP32-S3 avec USB natif.
  // Ajout d'un timeout pour ne pas bloquer si le moniteur n'est pas ouvert.
  unsigned long start_time = millis();
  while (!Serial && (millis() - start_time < 2000)) {
    delay(100);
  }

  Serial.println("Booting Dual Display Firmware...");
  Serial.flush(); // Force l'envoi des données
  // Initialise la broche de la LED comme une sortie
  pinMode(LED_PIN, OUTPUT);
  

  // Initialize LittleFS for asset loading
  // Le 'true' en second paramètre formate le système de fichiers s'il ne peut pas être monté.
  // C'est utile pour la première initialisation ou après une corruption.
  if (!LittleFS.begin(true)) {
    Serial.println("FATAL: LittleFS format/mount failed. Halting.");
    Serial.flush();
    // Si même le formatage échoue, il y a un problème matériel ou de configuration.
    while (1) {
      digitalWrite(LED_PIN, !digitalRead(LED_PIN)); // Clignotement rapide pour signaler une erreur fatale
      delay(100);
    }
  }

  sleep(1);

  // --- Initialisation de l'écran et du capteur désactivée pour le débogage ---
  // Initialize displays and load graphical assets
  init_tft();
  
  // Perform an initial clear of both physical screens to ensure a clean state
  clear_all_screens(TFT_BLACK);
  delay(50); // Short delay to ensure screens are cleared
  
  // Show splash screen to user while the rest initializes
  show_splash_screen();
  delay(1000); // Keep splash visible for a moment
  //
  // Initialize the ToF sensor (this part is slow)
  #if USE_TOF_SENSOR
    init_tof_sensor();
  #endif
  #if ENABLE_WIFI
    Serial.printf("Connecting to Wi-Fi: %s ...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    unsigned long wifi_start = millis();
    bool wifi_connected = true;
    while (WiFi.status() != WL_CONNECTED) {
      delay(250);
      Serial.print(".");
      if (millis() - wifi_start > 6000) { // 6 seconds timeout
        Serial.println("\nWi-Fi connection timed out. Continuing offline.");
        wifi_connected = false;
        break;
      }
    }
    if (wifi_connected) {
      Serial.println("\nWi-Fi Connected!");
      Serial.print("IP Address: ");
      Serial.println(WiFi.localIP());
      udp.begin(UDP_PORT);
      Serial.printf("UDP listener started on port %d\n", UDP_PORT);
    }
  #endif

  Serial.println("Initialization complete. Starting main loop.");
  Serial.flush();
}

// Forward declaration for the main application logic
void main_loop();

/**
 * @brief Main application loop.
 */
void loop() {
  // Call the main application logic
  main_loop();
}

void main_loop() {
  // --- FPS Calculation ---
  frame_count++;
  unsigned long current_millis = millis();
  if (current_millis - last_fps_time >= 1000) {
    // Calculate FPS over the last second
    current_fps = frame_count / ((current_millis - last_fps_time) / 1000.0f);
    last_fps_time = current_millis;
    frame_count = 0;
    Serial.printf("FPS: %.1f\n", current_fps);
    Serial.flush();
  }

  // --- 1. Sensor & Input Update ---
  handle_serial_input();
#if ENABLE_WIFI
  if (WiFi.status() == WL_CONNECTED) {
    handle_udp_input();
  }
#endif

  #if USE_TOF_SENSOR
    #if TOF_CALIBRATION_MODE
      // In calibration mode, force an update on every frame
      update_tof_sensor_data();
    #else
    update_tof_sensor_data();
    #endif
  #endif

  // Coordinated Target Selection (Correlation / Fallback Logic)
  TofTarget active_target;
  bool camera_active = (camera_target.is_valid && (millis() - last_camera_update_time < CAMERA_TIMEOUT_MS));

  if (camera_active) {
    active_target = camera_target;
  } else {
    camera_target.is_valid = false;
    #if USE_TOF_SENSOR
      active_target = get_tof_target();
    #else
      active_target.is_valid = false;
      active_target.x = 0.0f;
      active_target.y = 0.0f;
    #endif
  }

  // --- 2. Eye Position Logic ---
  // Update the logical positions of the eyes based on the active target
  update_eye_positions(active_target);

  // --- 3. Drawing ---
  for (int i = 0; i < NUM_EYES; i++) {
    select_screen(i);
    clear_buffer(TFT_BLACK);

    // Get the final calculated position and image type for the current eye
    EyePosition pos = get_eye_position(i);
    EyeImageType image_type = get_current_eye_image_type(active_target);

    // Draw the eye at its final calculated position
    draw_eye_at_target(pos.x, pos.y, 0, image_type); // 0 = eyelid open

    // Optional: Draw the ToF debug grid on one of the screens
    #if USE_TOF_SENSOR && SHOW_TOF_DEBUG_GRID
      if (i == EYE_RIGHT) { // Draw only on the right eye screen
        const int16_t grid_size = 80;
        const int16_t grid_pos = (SCR_WD - grid_size) / 2;
        // Get raw sensor data for display
        const VL53L5CX_ResultsData* tof_data = get_tof_measurement_data();
        // Use the same 'target' that was used for the eye movement
       draw_tof_debug_grid(grid_pos, grid_pos, grid_size, tof_data, active_target.min_dist_pixel_x, active_target.min_dist_pixel_y);

        // --- Draw FPS Counter ---
        char fps_str[10];
        dtostrf(current_fps, 4, 1, fps_str); // Format float to string (width 4, 1 decimal)
        char display_str[15];

        // --- Draw Battery Level ---
        int batt_level = get_battery_percentage();

        sprintf(display_str, "FPS:%s B:%d%%", fps_str, batt_level);
        drawString_fb(display_str, 5, 5, TFT_WHITE);
      }
    #endif
  }

  // --- 4. Display Update ---
  // Push the completed framebuffers to the physical screens
  display_all_buffers();
}