#include <Servo.h>

Servo baseServo;
Servo shoulderServo;
Servo elbowServo;
Servo forearmServo;
Servo wristServo;
Servo gripperServo;

void setup() {
  Serial.begin(9600);

  baseServo.attach(3);
  shoulderServo.attach(5);
  elbowServo.attach(6);
  forearmServo.attach(9);
  wristServo.attach(10);
  gripperServo.attach(11);
}

void loop() {
  if (Serial.available()) {

    int base = Serial.parseInt();
    int shoulder = Serial.parseInt();
    int elbow = Serial.parseInt();
    int forearm = Serial.parseInt();
    int wrist = Serial.parseInt();
    int gripper = Serial.parseInt();

    baseServo.write(base);
    shoulderServo.write(shoulder);
    elbowServo.write(elbow);
    forearmServo.write(forearm);
    wristServo.write(wrist);
    gripperServo.write(gripper);
    
  }
}