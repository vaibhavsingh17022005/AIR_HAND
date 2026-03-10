import cv2                                                          #OpenCV for video capture and display
import mediapipe as mp                                              #MediaPipe for hand tracking and landmark detection
import time                                                         #Time for calculating FPS and adding delays
import serial                                                       #Serial for communication with Arduino (if using serial communication instead of HTTP requests)
import math                                                         #Math for calculating distances and angles

mp_hands = mp.solutions.hands                                       
mp_draw = mp.solutions.drawing_utils                                

def main():
    last_send_time = 0
    send_delay = 0.08 
    Arduino = serial.Serial('COM5', 9600, timeout=1)                #Initialize serial communication with Arduino on COM5 at 9600 baud rate                                                        
    prev_angles = [90, 90, 90, 90, 90, 90]                          #Initial angle for gripper
    time.sleep(2)                                                   #Wait for Arduino to initialize

    cap = cv2.VideoCapture(0)                                       #Start video capture from the default webcam
    cap.set(3, 1280)                                                
    cap.set(4, 720)                                                 

    pTime = 0                                                       #Previous time for calculating FPS

    with mp_hands.Hands(                                            #Initialize MediaPipe Hands with specified parameters for hand detection and tracking
        max_num_hands=1,                                            
        min_detection_confidence=0.7,                               
        min_tracking_confidence=0.7,                                
    ) as hands:                                                     
        while True:                                                 #Main loop to continuously capture video frames, detect hand landmarks, and control Arduino based on hand gestures         
            attempt = 0                                             
            success, img = cap.read()                               
            while not success and attempt <5:                       #If reading the frame was not successful, wait for a short time and try again, up to 5 attempts
                time.sleep(0.2)                                     #Wait for 200 milliseconds before trying to read the frame again, to allow time for the camera to recover if it was temporarily unavailable
                success, img = cap.read()                           
                attempt += 1                                        
            if not success:                                         
                print("Failed to read frame")                       
                break                                               

            img = cv2.flip(img, 1)                                  
            h, w, _ = img.shape                                     
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)              
            results = hands.process(rgb)                            #Process the RGB image with MediaPipe Hands to detect hand landmarks;

            if results.multi_hand_landmarks:                        #If hand landmarks are detected in the current frame, proceed to loop through each detected hand and its landmarks to visualize them on the image and calculate the distance between the thumb and index finger to control the gripper angle on the Arduino, as well as display which fingers are up based on their landmark positions
                for hand_landmarks in results.multi_hand_landmarks: #Loop through each detected hand's landmarks to visualize them on the image and calculate the distance between the thumb and index finger to control the gripper angle on the Arduino, as well as display which fingers are up based on their landmark positions
                    mp_draw.draw_landmarks(                         #Draw the detected hand landmarks and connections on the image for visualization, using MediaPipe's drawing utilities to connect the landmarks according to the defined hand connections, which helps users see the detected hand structure and understand how their gestures are being interpreted by the program
                        img,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                    )
                    wrist = hand_landmarks.landmark[0]              #BASE - Move your hand along x-axis to control base servo (Wrist X position)
                    base = int(wrist.x * 180)
                    if abs(base - prev_angles[0]) < 4:
                        base = prev_angles[0]
                    

                    shoulder = int((1-wrist.y) * 180)                 #SHOULDER - Move your hand along y-axis to control shoulder servo (Wrist Y position)
                    if abs(shoulder - prev_angles[1]) < 4:
                        shoulder = prev_angles[1]

                    index_y = hand_landmarks.landmark[8].y          #ELBOW - Move your hand up and down to control elbow servo (Index finger Y positiion relative to pinky finger Y position)
                    pinky_y = hand_landmarks.landmark[20].y
                    elbow = int((index_y - pinky_y + 0.5) * 180)
                    if abs(elbow - prev_angles[2]) < 4:
                        elbow = prev_angles[2]

                    fingers = 0                                     #FOREARM - Raise fingers one by one at a time to control forearm servo (4 steps: 0 to 180 degrees)
                    for tip in [8, 12, 16, 20]:
                        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[tip-2].y:
                            fingers +=1
                    forearm = int((fingers / 4) * 180)

                    x1 = hand_landmarks.landmark[5].x               #WRIST - Rotate your wrist to control wrist servo (Angle between wrist and index finger)
                    y1 = hand_landmarks.landmark[5].y
                    x2 = hand_landmarks.landmark[17].x
                    y2 = hand_landmarks.landmark[17].y
                    angle_rad = math.atan2(y2 - y1, x2 - x1)
                    wrist_angle = int((angle_rad + math.pi) / (2 * math.pi) * 180)

                    thumb = hand_landmarks.landmark[4]              #GRIPPER - Pinch your thumb and index finger to control gripper
                    index = hand_landmarks.landmark[8]

                    x1, y1 = int(thumb.x * w), int(thumb.y * h)
                    x2, y2 = int(index.x * w), int(index.y * h)

                    distance = math.hypot(x2 - x1, y2 - y1)
                    gripper = int(min(distance, 200) / 200 * 180)

                    limits = [                                      #Apply limits to protect hardware
                        (0, 180),     #Base
                        (0, 180),     #Shoulder
                        (20, 160),     #Elbow
                        (0, 180),     #Forearm
                        (0, 180),     #Wrist
                        (0, 180)      #Gripper
                    ]

                    raw_angles = [base, shoulder, elbow, forearm, wrist_angle, gripper]

                    angles = []
                    for i in range(6):
                        low, high = limits[i]
                        val = max(low, min(raw_angles[i], high))
                        val = int(0.85 * prev_angles[i] + 0.15 * val)   #For smoother movements
                        angles.append(val)

                    threshold = 5

                    send = False
                    for i in range(6):
                        if abs(angles[i] - prev_angles[i]) > threshold:
                            send = True
                            break

                    current_time = time.time()
                    
                    if send and (current_time - last_send_time) > send_delay:
                        data = f"{angles[0]},{angles[1]},{angles[2]},{angles[3]},{angles[4]},{angles[5]}\n"
                        Arduino.write(data.encode())
                        prev_angles = angles.copy()
                        last_send_time = current_time

                    if hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y:
                        cv2.putText(img, "Index UP", (50,100),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (255,0,0), 2)
                    
                    if hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y:
                        cv2.putText(img, "Middle UP", (50,200),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (255,0,0), 2)
                    
                    if hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y:
                        cv2.putText(img, "Ring UP", (50,300),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (255,0,0), 2)
                        
                    if hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y:
                        cv2.putText(img, "Pinky UP", (50,400),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (255,0,0), 2)
                    
                    if hand_landmarks.landmark[4].y < hand_landmarks.landmark[3].y:
                        cv2.putText(img, "Thumb UP", (50,500),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (255,0,0), 2)

                    finger_tips = {
                        "Thumb": hand_landmarks.landmark[4],
                        "Index": hand_landmarks.landmark[8],
                        "Middle": hand_landmarks.landmark[12],
                        "Ring": hand_landmarks.landmark[16],
                        "Pinky": hand_landmarks.landmark[20],
                    }

                    for name, landmark in finger_tips.items():
                        x, y = int(landmark.x * w), int(landmark.y * h)
                        cv2.putText(
                            img,
                            name,
                            (x, y - 10),
                            cv2. FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255,255,255),
                            1,
                        )

                        cv2.circle(
                            img,
                            (x, y),
                            5,
                            (0, 255, 0),
                            -1
                        )
            
            cTime = time.time()
            fps = 1/(cTime - pTime)
            pTime = cTime

            cv2.putText(img, f'FPS: {int(fps)}',
                        (20,50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0,0,255),
                        2)

            cv2.imshow("Image", img)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    Arduino.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()