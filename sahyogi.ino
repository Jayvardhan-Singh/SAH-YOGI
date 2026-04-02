const int sensorPin = A0; 

void setup() {
  // 115200 baud rate ensures zero lag between Arduino and Python
  Serial.begin(115200); 
}

void loop() {
  int sensorValue = analogRead(sensorPin);
  Serial.println(sensorValue);
  
  // A tiny delay keeps the serial stream stable without affecting the 60FPS game loop
  delay(10); 
}
