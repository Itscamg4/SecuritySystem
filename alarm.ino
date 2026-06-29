#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// ── User config — change these before flashing ─────────────────────────────

const char* WIFI_SSID     = "";
const char* WIFI_PASSWORD = "";

// Paste the URL shown in the Python app's "ESP8266 URL" field:
const char* SERVER_URL    = "";

const unsigned long HTTP_COOLDOWN_MS = 3000;

#define trigPin MOSI   // GPIO 13  D7
#define echoPin MISO   // GPIO 12  D6
#define led     SCK    // GPIO 14  D5
#define buzzer  SDA    // GPIO  4  D2


float        new_delay      = 30;
unsigned long lastHttpAlert = 0;


void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("[WiFi] Connected — IP: ");
  Serial.println(WiFi.localIP());
}


void sendAlert(long distance) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP]  Skipped — WiFi not connected");
    return;
  }

  WiFiClient client;
  HTTPClient http;

  http.begin(client, SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(3000);  // don't let a slow network stall the loop

  String payload = "{\"distance\":" + String(distance) + "}";
  int    code    = http.POST(payload);

  if (code > 0) {
    Serial.println("[HTTP]  Alert sent — HTTP " + String(code));
  } else {
    Serial.println("[HTTP]  Request failed: " + http.errorToString(code));
  }

  http.end();
}


void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(buzzer,  OUTPUT);
  pinMode(led,     OUTPUT);

  connectWiFi();
  Serial.println("Ready — monitoring started.");
}


void loop() {
  // Reconnect automatically if WiFi drops
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi]  Connection lost — reconnecting...");
    connectWiFi();
  }

  // Ultrasonic pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH);
  long distance = (duration / 2) / 29.1;
  new_delay     = (distance * 3) + 30;

  Serial.print(distance);
  Serial.println(" cm");

  if (distance > 0 && distance < 240){
    Serial.println("DETECTED");
    digitalWrite(buzzer, HIGH);
    digitalWrite(led,    HIGH);

    // Send HTTP alert, but respect the local cooldown so we
    // don't hammer the server on every loop iteration
    unsigned long now = millis();
    if (now - lastHttpAlert > HTTP_COOLDOWN_MS) {
      sendAlert(distance);
      lastHttpAlert = now;
    }

    delay((long)new_delay);
    digitalWrite(buzzer, LOW);
    digitalWrite(led,    LOW);
  }else{
    digitalWrite(buzzer, LOW);
    digitalWrite(led,    LOW);
  }

  delay(200);
}
