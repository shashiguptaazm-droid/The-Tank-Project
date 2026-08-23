#ifndef BME688_SENSOR_H
#define BME688_SENSOR_H

#include <Adafruit_BME680.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// I2C Pin Configuration (Safe for ESP32-S3 AI Camera)
#define BME_SDA_PIN 11  // Safe - not used by camera
#define BME_SCL_PIN 13  // Safe - not used by camera

// I2C Address Configuration
#define BME_ADDRESS_PRIMARY 0x76    // Try this first (CSB pulled to GND)
#define BME_ADDRESS_SECONDARY 0x77  // Fallback (CSB pulled to VDDIO)

// Self-heating compensation (BME688 readings can be 5-10°C higher than ambient)
#define BME_SELF_HEATING_OFFSET 5.0  // Degrees Celsius

class BME688_Sensor {
private:
    Adafruit_BME680 bme;
    float tempOffset;
    bool initialized;
    
public:
    BME688_Sensor() : tempOffset(BME_SELF_HEATING_OFFSET), initialized(false) {}
    
    // Initialize the sensor with fallback address logic
    bool begin() {
        // Initialize I2C with safe pins
        Wire.begin(BME_SDA_PIN, BME_SCL_PIN);
        
        Serial.println("\n[BME688] Initializing sensor...");
        Serial.printf("[BME688] Using I2C SDA=GPIO%d, SCL=GPIO%d\n", BME_SDA_PIN, BME_SCL_PIN);
        
        // Try primary address (0x76)
        if (bme.begin(BME_ADDRESS_PRIMARY, &Wire)) {
            Serial.printf("[BME688] ✓ Sensor found at address 0x%02X (PRIMARY)\n", BME_ADDRESS_PRIMARY);
            initialized = true;
            return configureAndVerify();
        }
        
        Serial.printf("[BME688] × Sensor not found at 0x%02X, trying fallback...\n", BME_ADDRESS_PRIMARY);
        
        // Try secondary address (0x77)
        if (bme.begin(BME_ADDRESS_SECONDARY, &Wire)) {
            Serial.printf("[BME688] ✓ Sensor found at address 0x%02X (FALLBACK)\n", BME_ADDRESS_SECONDARY);
            initialized = true;
            return configureAndVerify();
        }
        
        Serial.println("[BME688] × SENSOR NOT FOUND: Failed at both addresses 0x76 and 0x77");
        Serial.println("[BME688] × Troubleshooting:");
        Serial.println("[BME688]   - Verify I2C wiring (SDA→GPIO11, SCL→GPIO13)");
        Serial.println("[BME688]   - Check pull-up resistors (typically 4.7kΩ)");
        Serial.println("[BME688]   - Confirm sensor power (3.3V) and GND connection");
        Serial.println("[BME688]   - Verify CSB pin state for correct I2C address");
        initialized = false;
        return false;
    }
    
    // Read temperature with self-heating offset correction
    bool readTemperature(float& tempCelsius) {
        if (!initialized) {
            return false;
        }
        
        // Perform measurement
        if (!bme.performReading()) {
            Serial.println("[BME688] × Failed to perform reading");
            return false;
        }
        
        // Get temperature and apply offset correction
        float rawTemp = bme.temperature;
        tempCelsius = rawTemp - tempOffset;
        
        return true;
    }
    
    // Get all sensor readings
    bool getFullReading(float& temp, float& pressure, float& humidity, float& gas) {
        if (!initialized) {
            return false;
        }
        
        if (!bme.performReading()) {
            return false;
        }
        
        temp = bme.temperature - tempOffset;
        pressure = bme.pressure / 100.0;  // Convert to hPa
        humidity = bme.humidity;
        gas = bme.gas_resistance / 1000.0;  // Convert to kΩ
        
        return true;
    }
    
    // Check if sensor is initialized
    bool isInitialized() const {
        return initialized;
    }
    
    // Set custom self-heating offset
    void setTemperatureOffset(float offset) {
        tempOffset = offset;
        Serial.printf("[BME688] Temperature offset set to: %.1f°C\n", tempOffset);
    }
    
private:
    // Configure sensor and verify operation
    bool configureAndVerify() {
        // Set oversampling settings for best accuracy
        bme.setTemperatureOversampling(BME680_OS_8X);
        bme.setPressureOversampling(BME680_OS_4X);
        bme.setHumidityOversampling(BME680_OS_2X);
        bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
        bme.setGasHeater(320, 150);  // 320°C for 150ms (standard config)
        
        Serial.println("[BME688] Configuration complete:");
        Serial.printf("[BME688]   - Temperature oversampling: 8x\n");
        Serial.printf("[BME688]   - Pressure oversampling: 4x\n");
        Serial.printf("[BME688]   - Humidity oversampling: 2x\n");
        Serial.printf("[BME688]   - IIR Filter: Enabled\n");
        Serial.printf("[BME688]   - Gas heater: 320°C, 150ms\n");
        Serial.printf("[BME688]   - Self-heating offset: %.1f°C\n", tempOffset);
        Serial.println("[BME688] Ready to read data!");
        
        return true;
    }
};

#endif  // BME688_SENSOR_H