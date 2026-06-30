When replicating, customize the wiring guide to fit your own Arduino. In this project I utilized an ESP8226 microcontroller for the WiFi feature.
To utilize the email notifications, you will need to utilize the WiFi features for Python to run wirelessly. 
Be sure to enter your SENDER_EMAIL, SENDER_PASSWORD, to the Python script and WiFi_SSID, WiFi_PASSWORD, and SERVER_URL which contains your IP Address to the Arduino.

Built a WiFi-based security alarm using an ESP8266 microcontroller and a custom Python app.
The ESP8266 runs an ultrasonic sensor that watches for movement. When something gets close, it flips on a buzzer and LED, then sends an alert over WiFi to a server running on my computer.
On the backend, I wrote a Flask app to catch those alerts and built a Tkinter GUI on top of it so I can monitor everything live, set the cooldown time, and configure where email alerts go. When the sensor trips, the system fires off an email automatically through SMTP, with a cooldown built in so it doesn't spam your inbox every few seconds.
This one touched a lot of different skills: embedded C++ for the microcontroller, handling WiFi connections and reconnects, building a REST API with Flask, running multiple threads so the GUI and server don't block each other, and putting together a usable desktop interface.
Tech stack: C++ (Arduino/ESP8266), Python, Flask, Tkinter, SMTP, HTTP
