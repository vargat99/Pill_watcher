#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include <Wire.h>
#include "AS5600.h"
#include <Preferences.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <TaskScheduler.h>
#include <SPIFFS.h>
#include "Update.h"
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFiClient.h>


#define FIRMWARE_VERSION "3.0.0"
#define MYTZ "CET-1CEST,M3.5.0,M10.5.0/3"
#define I2C_SDA 14
#define I2C_SCL 15
#define MOTOR_PIN1 13
#define MOTOR_PIN2 2
#define LAMP_PIN 4

#define PORT 443
#define FILE_NAME "firmware.bin"

// Camera pins (for ESP32-CAM AI-Thinker)
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

#define PICTURE_UPLOAD_SECS 10
#define UPDATE_SETPOS_SECS 1
#define CHECK_POSITION_MILIS 10
#define SYNC_WITH_SERVER_HOURS 24
#define SYNC_SETTINGS_HOURS 1

Preferences preferences;

// Task sheculer
Scheduler runner;

// Tasks
void captureAndUploadImage();
void checkTimeAndUpdateSetpos();
void checkPosition();
void syncTime();
void checkForUpdate();
void syncSettings();
Task captureAndUploadImageTask(PICTURE_UPLOAD_SECS* TASK_SECOND, TASK_FOREVER, &captureAndUploadImage);
Task checkTimeAndUpdateSetposTask(UPDATE_SETPOS_SECS* TASK_SECOND, TASK_FOREVER, &checkTimeAndUpdateSetpos);
Task checkPositionTask(CHECK_POSITION_MILIS* TASK_MILLISECOND, TASK_FOREVER, &checkPosition);
Task syncTimeTask(SYNC_WITH_SERVER_HOURS* TASK_HOUR, TASK_FOREVER, &syncTime);
Task checkForUpdateTask(SYNC_WITH_SERVER_HOURS* TASK_HOUR, TASK_FOREVER, &checkForUpdate);
Task syncSettingsTask(SYNC_SETTINGS_HOURS* TASK_HOUR, TASK_FOREVER, &syncSettings);

// Your Flask server's upload endpoint
const char* serverName = "https://spencer-backend-4yvy33juha-lm.a.run.app";
// Timer variables
unsigned long previousMillis = 0;
const long interval = 10000;  // Interval to send a picture (in milliseconds)

// Access point name for configuration mode
bool APmode = false;
const char* ap_ssid = "Gyogyszeradagolo-WiFi";
WebServer server(80);

// Active position keeping
bool active = true;
int error_margin = 40;
int setpos = 0;
//int encoder_positions[21] = { 2286, 2100, 1906, 1713, 1517, 1309, 1114, 928, 746, 547, 352, 146, 4054, 3860, 3666, 3472, 3283, 3084, 2892, 2694, 2486 };
int encoder_positions[21] = { 159, 401, 602, 713, 858, 1035, 1224, 1411, 1590, 1780, 2046, 2325, 2571, 2739, 2864, 3035, 3193, 3391, 3580, 3770, 3977 };

// Settings
int morning_hour = 0;
int noon_hour = 11;
int night_hour = 15;
int picture_delay_secs = 60;
bool use_flash = false;

// Encoder
TwoWire I2CSensors = TwoWire(0);
AS5600 as5600(&I2CSensors);

// Hostname
String hostname = "";

// API key
String api_key = "supersecret";

// MQTT client
void mqttCallback(char* topic, byte* payload, unsigned int length);
const char* mqtt_server = "test.mosquitto.org";
const char* topic = "Spencer/test/status";
IPAddress myIP(0, 0, 0, 0);
IPAddress allZeros(0, 0, 0, 0);
IPAddress mqttBroker(192, 168, 0, 101);
WiFiClient wifiClient;
PubSubClient mqttClient(mqttBroker, 1883, mqttCallback, wifiClient);


void setup() {
  Serial.begin(115200);

  preferences.begin("settings", false);
  loadSettings();

  // Init motor
  pinMode(MOTOR_PIN1, OUTPUT);
  pinMode(MOTOR_PIN2, OUTPUT);
  digitalWrite(MOTOR_PIN1, LOW);
  digitalWrite(MOTOR_PIN2, LOW);

  // Init lamp
  pinMode(LAMP_PIN, OUTPUT);
  digitalWrite(LAMP_PIN, LOW);

  // Connect to WiFi using stored credentials
  connectToWiFi();

  // If failed to connect, start configuration mode
  if (WiFi.status() != WL_CONNECTED) {
    APmode = true;
    startConfigPortal();

    // Configure mDNS
    if (!MDNS.begin("gyogyszer")) {
      Serial.println("Error setting up MDNS responder!");
    } else {
      Serial.println("MDNS responder started");
    }

    // Associate mDNS name with the server
    MDNS.addService("http", "tcp", 80);

    // Route for root / web page
    server.on("/", HTTP_GET, handleRoot);

    // Route to save WiFi credentials
    server.on("/save", HTTP_POST, saveConfig);

    // Start server
    server.begin();
  } else {
    // Sync time with NTP
    configTzTime(MYTZ, "time.google.com", "time.windows.com", "pool.ntp.org");

    // Connect to MQTT server
    if (mqttClient.connect("painlessMeshClient", topic, 1, true, "OFFLINE")) {
      Serial.println("Connected to MQTT broker");
      mqttClient.publish(topic, "ONLINE");
    } else {
      Serial.println("Failed to connect to MQTT broker, restarting.");
      Serial.print("Fail reason: ");
      Serial.println(mqttClient.state());
      // delay(3000);
      // ESP.restart();
    }

    // Configure camera
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
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.jpeg_quality = 8;
    config.fb_count = 1;
    config.frame_size = FRAMESIZE_UXGA;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.sccb_i2c_port = 1;

    // Camera init
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
      Serial.printf("Camera init failed with error 0x%x", err);
      delay(1000);
      ESP.restart();
    }

    // Init encoder
    Serial.println(__FILE__);
    Serial.print("AS5600_LIB_VERSION: ");
    Serial.println(AS5600_LIB_VERSION);

    I2CSensors.begin(I2C_SDA, I2C_SCL, 100000);

    as5600.begin(4);                         //  set direction pin.
    as5600.setDirection(AS5600_CLOCK_WISE);  //  default, just be explicit.
    int b = as5600.isConnected();
    Serial.print("Connect: ");
    Serial.println(b);

    // Hostname
    hostname = preferences.getString("hostname", "");
    if (hostname.length() == 0) {
      hostname = "Spencer" + WiFi.macAddress().substring(9);
      hostname.replace(":", "");
      preferences.putString("hostname", hostname);
    }
    Serial.print("Hostname: ");
    Serial.println(hostname);

    // Taskshecduler
    runner.init();
    runner.addTask(captureAndUploadImageTask);
    runner.addTask(checkTimeAndUpdateSetposTask);
    runner.addTask(checkPositionTask);
    runner.addTask(syncTimeTask);
    runner.addTask(checkForUpdateTask);
    runner.addTask(syncSettingsTask);
    captureAndUploadImageTask.enable();
    checkTimeAndUpdateSetposTask.enable();
    checkPositionTask.enable();
    syncTimeTask.enable();
    checkForUpdateTask.enable();
    syncSettingsTask.enable();
  }
}

void loop() {
  if (APmode) {
    server.handleClient();
  } else {
    runner.execute();
  }
}

void captureAndUploadImage() {
  if (use_flash) {
    digitalWrite(LAMP_PIN, HIGH);
    delay(50);
  }
  camera_fb_t* fb = esp_camera_fb_get();
  digitalWrite(LAMP_PIN, LOW);
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
    String contentType = "multipart/form-data; boundary=" + boundary;
    String path = String(serverName) + "/upload";
    http.begin(path);
    http.addHeader("Content-Type", contentType);

    // Get the current timestamp
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
      Serial.println("Failed to obtain time");
      esp_camera_fb_return(fb);
      return;
    }
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    // Add timestamp to header
    http.addHeader("X-Timestamp", String(timestamp));

    // Add hostname to header
    http.addHeader("Hostname", hostname);

    // Add apikey to header
    http.addHeader("X-API-Key", api_key);

    // Add current encoder position to header
    int currentpos = as5600.readAngle();
    http.addHeader("Encoder-Position", String(currentpos));
    Serial.println(currentpos);

    String filename = hostname + "-" + String(timestamp) + ".jpg";
    String bodyStart = "--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"" + filename + "\"\r\nContent-Type: image/jpeg\r\n\r\n";
    String bodyEnd = "\r\n--" + boundary + "--\r\n";

    int bodyLength = bodyStart.length() + fb->len + bodyEnd.length();

    // Allocate buffer for full request body
    uint8_t* requestBody = (uint8_t*)malloc(bodyLength);
    if (!requestBody) {
      Serial.println("Failed to allocate memory for request body");
      esp_camera_fb_return(fb);
      return;
    }

    // Fill the request body buffer
    memcpy(requestBody, bodyStart.c_str(), bodyStart.length());
    memcpy(requestBody + bodyStart.length(), fb->buf, fb->len);
    memcpy(requestBody + bodyStart.length() + fb->len, bodyEnd.c_str(), bodyEnd.length());

    http.addHeader("Content-Length", String(bodyLength));

    int httpResponseCode = http.POST(requestBody, bodyLength);

    if (httpResponseCode > 0) {
      Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    } else {
      Serial.printf("Error code: %s\n", http.errorToString(httpResponseCode).c_str());
    }

    http.end();

    free(requestBody);  // Free the allocated memory
  } else {
    Serial.println("WiFi Disconnected");
  }

  esp_camera_fb_return(fb);
}

// Connect to wifi with the stored credentials
void connectToWiFi() {
  String ssid = preferences.getString("ssid", "");
  String password = preferences.getString("password", "");

  // Connect to WiFi if stored credentials exist
  if (ssid.length() > 0 && password.length() > 0) {
    WiFi.begin(ssid.c_str(), password.c_str());
    Serial.println("Connecting to WiFi using stored credentials...");
    int attempt = 0;
    while (WiFi.status() != WL_CONNECTED && attempt < 10) {
      delay(1000);
      Serial.print(".");
      attempt++;
    }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("WiFi connected successfully");
    } else {
      Serial.println("Failed to connect to WiFi using stored credentials");
    }
  } else {
    Serial.println("No stored WiFi credentials found");
  }
}

// Starting AP to configure WiFi credentials
void startConfigPortal() {
  Serial.println("Starting configuration portal...");

  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid);

  Serial.println("Connect to AP: " + String(ap_ssid));
  Serial.println("IP: " + String(WiFi.localIP()));
}

// Webpage for WiFi config
void handleRoot() {
  server.send(200, "text/html", "<h1>ESP32 WiFi Configuration Page</h1><form method='POST' action='/save'><label>SSID: <input type='text' name='ssid'></label><br><label>Password: <input type='password' name='password'></label><br><input type='submit' value='Save'></form>");
}

// Save WiFi crecentials
void saveConfig() {
  String ssid = server.arg("ssid");
  String password = server.arg("password");

  preferences.putString("ssid", ssid);
  preferences.putString("password", password);

  server.send(200, "text/plain", "Credentials saved. Restarting...");
  delay(1000);
  ESP.restart();
}

// Check the time and update the setposition
void checkTimeAndUpdateSetpos() {
  tm rtcTime;
  getLocalTime(&rtcTime);
  int hour = rtcTime.tm_hour;

  int index = rtcTime.tm_wday * 3;
  if (hour < morning_hour) {
    index -= 1;
  } else if (hour < noon_hour) {
    index += 0;
  } else if (hour < night_hour) {
    index += 1;
  } else {
    index += 2;
  }

  if (index < 0) {
    index = 20;
  }

  if (active) {
    setpos = encoder_positions[index];
  }
}

// Position controll
void checkPosition() {
  int currentpos = as5600.readAngle();
  int error = setpos - currentpos;
  // Serial.print("Current setpos: ");
  // Serial.println(setpos);
  // Serial.print("Error: ");
  // Serial.println(error);

  if (abs(error) > error_margin) {
    if (error < 0) {
      digitalWrite(MOTOR_PIN1, HIGH);
      digitalWrite(MOTOR_PIN2, LOW);
    } else {
      digitalWrite(MOTOR_PIN1, LOW);
      digitalWrite(MOTOR_PIN2, HIGH);
    }
  } else {
    digitalWrite(MOTOR_PIN1, LOW);
    digitalWrite(MOTOR_PIN2, LOW);
  }
}

// Sync with NTP server
void syncTime() {
  Serial.println("Syncing time");
  configTzTime(MYTZ, "time.google.com", "time.windows.com", "pool.ntp.org");
}

// Check if firmware update is avaiable
void checkForUpdate() {
  Serial.println("Checking for update");
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    // Specify the URL
    String path = String(serverName) + "/check_update";
    http.begin(path);

    // Add headers
    http.addHeader("Hostname", hostname);  // Replace with appropriate hostname if needed

    // Send the request
    int httpResponseCode = http.GET();

    if (httpResponseCode > 0) {
      // Get the response payload
      String payload = http.getString();
      Serial.println("HTTP Response code: " + String(httpResponseCode));
      Serial.println("Response: " + payload);
      if (httpResponseCode == 200) {

        // Parse JSON
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, payload);
        if (!error) {
          const char* host = doc["host"];
          const char* path = doc["path"];

          // Print the extracted values
          Serial.println("Host: " + String(host));
          Serial.println("Path: " + String(path));

          getFileFromServer(String(host), String(path));
          performOTAUpdateFromSPIFFS();
        } else {
          Serial.print("deserializeJson() failed: ");
          Serial.println(error.f_str());
        }
      }
    } else {
      Serial.println("Error on HTTP request");
    }

    // Free resources
    http.end();
  } else {
    Serial.println("WiFi not connected");
  }
}

// Check if settings sould be updated
void syncSettings() {
  Serial.println("Syncing settings");
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    // Specify the URL
    String path = String(serverName) + "/get_settings";
    http.begin(path);

    // Add headers
    http.addHeader("Hostname", hostname);  // Replace with appropriate hostname if needed

    // Send the request
    int httpResponseCode = http.GET();

    if (httpResponseCode > 0) {
      // Get the response payload
      String payload = http.getString();
      Serial.println("HTTP Response code: " + String(httpResponseCode));
      Serial.println("Response: " + payload);
      if (httpResponseCode == 200) {

        // Parse JSON
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, payload);
        if (!error) {
          int morning_hour = doc["morning_time"];
          int noon_hour = doc["noon_time"];
          int evening_hour = doc["evening_time"];
          int picture_delay_secs = doc["picture_delay"];
          bool use_flash = doc["use_flash"];

          // Print the extracted values
          Serial.println("Morning hour: " + String(morning_hour));
          Serial.println("Noon hour: " + String(noon_hour));
          Serial.println("Evening hour: " + String(evening_hour));
          Serial.println("Picture delay: " + String(picture_delay_secs));
          Serial.println("Use flash: " + String(use_flash));

          // Update settings in prefrences
          saveCurrentSettings();
        } else {
          Serial.print("deserializeJson() failed: ");
          Serial.println(error.f_str());
        }
      }
    } else {
      Serial.println("Error on HTTP request");
    }

    // Free resources
    http.end();
  } else {
    Serial.println("WiFi not connected");
  }
}

void getFileFromServer(String host, String path) {
  WiFiClientSecure client;
  client.setInsecure();  // Set client to allow insecure connections

  if (client.connect(host.c_str(), PORT)) {  // Connect to the server
    Serial.println("Connected to server");
    client.print("GET " + path + " HTTP/1.1\r\n");  // Send HTTP GET request
    client.print("Host: " + host + "\r\n");         // Specify the host
    client.println("Connection: close\r\n");        // Close connection after response
    client.println();                               // Send an empty line to indicate end of request headers

    File file = SPIFFS.open("/" + String(FILE_NAME), FILE_WRITE);  // Open file in SPIFFS for writing
    if (!file) {
      Serial.println("Failed to open file for writing");
      return;
    }

    bool endOfHeaders = false;
    String headers = "";
    String http_response_code = "error";
    const size_t bufferSize = 1024;  // Buffer size for reading data
    uint8_t buffer[bufferSize];

    // Loop to read HTTP response headers
    while (client.connected() && !endOfHeaders) {
      if (client.available()) {
        char c = client.read();
        headers += c;
        if (headers.startsWith("HTTP/1.1")) {
          http_response_code = headers.substring(9, 12);
        }
        if (headers.endsWith("\r\n\r\n")) {  // Check for end of headers
          endOfHeaders = true;
        }
      }
    }

    Serial.println("HTTP response code: " + http_response_code);  // Print received headers

    // Loop to read and write raw data to file
    while (client.connected()) {
      if (client.available()) {
        size_t bytesRead = client.readBytes(buffer, bufferSize);
        file.write(buffer, bytesRead);  // Write data to file
      }
    }
    file.close();   // Close the file
    client.stop();  // Close the client connection
    Serial.println("File saved successfully");
  } else {
    Serial.println("Failed to connect to server");
  }
}

void performOTAUpdateFromSPIFFS() {
  // Open the firmware file in SPIFFS for reading
  File file = SPIFFS.open("/" + String(FILE_NAME), FILE_READ);
  if (!file) {
    Serial.println("Failed to open file for reading");
    return;
  }

  Serial.println("Starting update..");
  size_t fileSize = file.size();  // Get the file size
  Serial.println(fileSize);

  // Begin OTA update process with specified size and flash destination
  if (!Update.begin(fileSize, U_FLASH)) {
    Serial.println("Cannot do the update");
    return;
  }

  // Write firmware data from file to OTA update
  Update.writeStream(file);

  // Complete the OTA update process
  if (Update.end()) {
    Serial.println("Successful update");
  } else {
    Serial.println("Error Occurred:" + String(Update.getError()));
    return;
  }

  file.close();  // Close the file
  Serial.println("Reset in 4 seconds....");
  delay(4000);
  ESP.restart();  // Restart ESP32 to apply the update
}

// Save current settings to prefrences
void saveCurrentSettings() {
  preferences.putInt("morning_hour", morning_hour);
  preferences.putInt("noon_hour", noon_hour);
  preferences.putInt("night_hour", night_hour);
  preferences.putInt("picture_delay_secs", picture_delay_secs);
  preferences.putBool("use_flash", use_flash);

  captureAndUploadImageTask.setInterval(picture_delay_secs * TASK_SECOND);
}

// Load and apply settings from prefrences
void loadSettings() {
  morning_hour = preferences.getInt("morning_hour", 6);
  noon_hour = preferences.getInt("noon_hour", 11);
  night_hour = preferences.getInt("night_hour", 15);
  picture_delay_secs = preferences.getInt("picture_delay_secs", 60);
  use_flash = preferences.getBool("use_flash", false);

  captureAndUploadImageTask.setInterval(picture_delay_secs * TASK_SECOND);
}

// This is the callback when the node recives message from the MQTT
void mqttCallback(char* topic, uint8_t* payload, unsigned int length) {
  char* cleanPayload = (char*)malloc(length + 1);
  memcpy(cleanPayload, payload, length);
  cleanPayload[length] = '\0';
  String msg = String(cleanPayload);
  free(cleanPayload);

  String topicString = String(topic);
  Serial.print("Topic: ");
  Serial.println(topicString);
}