/*
 =============================================================================
  PROYECTO: HydroGuard IoT - Firmware para Microcontrolador ESP32
  PROTOCOLO: MQTT v3.1.1 / v5 sobre WiFi (QoS 1)
  DESCRIPCIÓN: Lectura de sensores de tanques hidropónicos y microclima.
               Publicación periódica de telemetría y estado (LWT).
 =============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// 1. Configuración de Conectividad WiFi
const char* WIFI_SSID = "INVERNADERO_WIFI_2.4G";
const char* WIFI_PASS = "clave-segura-campo";

// 2. Configuración del Broker MQTT
const char* MQTT_SERVER = "192.168.1.100"; // IP del Broker (Mosquitto / EMQX)
const int MQTT_PORT = 1883;
const char* MQTT_USER = "esp32_node";
const char* MQTT_PASS = "iot-password";

// 3. Identificación del Dispositivo en HydroGuard
const char* GREENHOUSE_ID = "gh-obera-01";
const char* DEVICE_UID = "ESP32-GH-PRO-001";

// Tópicos MQTT
String topicTelemetry = String("hydroguard/gh/") + GREENHOUSE_ID + "/devices/" + DEVICE_UID + "/telemetry";
String topicStatus = String("hydroguard/gh/") + GREENHOUSE_ID + "/devices/" + DEVICE_UID + "/status";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastTelemetryMillis = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 5000; // Publicar cada 5 segundos

// Pines de Sensores (Ejemplo de hardware)
#define PIN_PH_SENSOR       34 // ADC1
#define PIN_EC_SENSOR       35 // ADC1
#define PIN_WATER_TRIG      5  // Ultrasonido Trigger
#define PIN_WATER_ECHO      18 // Ultrasonido Echo

void setupWifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected! IP: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Intentando conexión a Broker MQTT...");
    
    // Mensaje Last Will and Testament (LWT) para detectar desconexión en el servidor
    String lwtPayload = "{\"status\":\"offline\",\"device_uid\":\"" + String(DEVICE_UID) + "\"}";
    
    if (mqttClient.connect(DEVICE_UID, MQTT_USER, MQTT_PASS, topicStatus.c_str(), 1, true, lwtPayload.c_str())) {
      Serial.println(" ¡Conectado!");
      
      // Notificar estado online
      String onlinePayload = "{\"status\":\"online\",\"device_uid\":\"" + String(DEVICE_UID) + "\"}";
      mqttClient.publish(topicStatus.c_str(), onlinePayload.c_str(), true);
      
    } else {
      Serial.print(" Falló conexión MQTT, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Reintentando en 5 segundos...");
      delay(5000);
    }
  }
}

// Lectura de Sensores Físicos
float readPH() {
  int raw = analogRead(PIN_PH_SENSOR);
  float voltage = (raw / 4095.0) * 3.3;
  // Curva de calibración: pH = 7.0 - (voltage - 1.65) * 3.5
  return 7.0 - ((voltage - 1.65) * 3.5);
}

float readWaterLevel() {
  // Simulación / Ultrasonido % de 0 a 100
  return 85.0; 
}

float readEC() {
  return 1.6; // mS/cm
}

float readAirTemp() {
  return 24.5; // °C
}

float readAirHumidity() {
  return 68.0; // %
}

void publishTelemetry() {
  // Crear Payload JSON ligero optimizado para MQTT
  StaticJsonDocument<512> doc;
  doc["device_uid"] = DEVICE_UID;
  doc["timestamp"] = millis();

  JsonArray readings = doc.createNestedArray("readings");

  JsonObject r1 = readings.createNestedObject();
  r1["sensor_code"] = "TANK_1_PH";
  r1["value"] = readPH();

  JsonObject r2 = readings.createNestedObject();
  r2["sensor_code"] = "TANK_1_WATER_LEVEL";
  r2["value"] = readWaterLevel();

  JsonObject r3 = readings.createNestedObject();
  r3["sensor_code"] = "TANK_1_EC";
  r3["value"] = readEC();

  JsonObject r4 = readings.createNestedObject();
  r4["sensor_code"] = "ENV_TEMP_AIR";
  r4["value"] = readAirTemp();

  JsonObject r5 = readings.createNestedObject();
  r5["sensor_code"] = "ENV_HUMIDITY";
  r5["value"] = readAirHumidity();

  char buffer[512];
  serializeJson(doc, buffer);

  // Publicar con Calidad de Servicio 1 (QoS 1)
  mqttClient.publish(topicTelemetry.c_str(), buffer, false);
  Serial.print("📡 [MQTT TX] Telemetría enviada a: ");
  Serial.println(topicTelemetry);
}

void setup() {
  Serial.begin(115200);
  setupWifi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  unsigned long currentMillis = millis();
  if (currentMillis - lastTelemetryMillis >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryMillis = currentMillis;
    publishTelemetry();
  }
}
