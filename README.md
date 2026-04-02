# SAHYOGI

A smooth-scrolling, procedurally generated arcade racing game built in Python using Pygame. Navigate a custom-built mathematical road, dodge or burst through custom obstacles, and control your car using either your keyboard or a physical Arduino sensor!

## ✨ Features
* **Procedural Track Generation:** Customize the amplitude and durations of your track segments to create unique, perfectly smooth roads using cosine interpolation.
* **Constant Thickness Math:** Advanced calculus (derivatives and normal vectors) ensures the road remains exactly the same width, even on the steepest drops.
* **Custom Sprites & Audio:** Drop in your own `player.png`, distraction images, and a `pop.wav` sound effect to completely personalize the game.
* **Particle Physics:** Burst through distractions or crash into walls to trigger a fiery particle explosion.
* **Hybrid Controls & Smart Calibration:** Play with Keyboard arrows, or plug in an Arduino. The game features an interactive Blue/Red screen calibration sequence to dynamically map *any* analogue sensor's physical limits to the screen.
* **Jitter Filtering:** Built-in Exponential Moving Average (EMA) math keeps your hardware controls buttery smooth.

# 🛠️ Software Setup (Python)
Ensure you have Python 3.x installed on your computer.

Open your terminal or command prompt and install the required libraries:

Bash

`pip install pygame pyserial`

Run the game:
Bash

`python sahyogi.py`

# 🔌 Hardware Setup (Arduino - Optional)
You can use almost any analogue sensor (Potentiometer, Joystick, Light Sensor, or Ultrasonic Distance Sensor) to control the car.

## Wiring a Generic Analogue Sensor (e.g., Potentiometer)
VCC ➡️ Arduino 5V

GND ➡️ Arduino GND

Signal ➡️ Arduino A0

The Arduino Code (sahyogi.ino)
Upload this code to your Arduino using the Arduino IDE. Make sure the Serial Monitor is closed before launching the Python game!

# 🎮 How to Play
1. Main Menu (Track Designer)
Amplitude: How high/low the hills go (Max: 450).

Durations (A, B, C, D): Time in seconds for the Rise, Top Straight, Fall, and Bottom Straight (Max: 10s each).

Cycles: How many times the pattern repeats.

Click START when ready.

2. Smart Calibration (Arduino Mode Only)
If an Arduino is detected, the game will map your physical hardware's range of motion to the screen:

BLUE SCREEN (Top Limit): Move your sensor (or twist your knob) to the position you want to represent the "Top" of the screen. Press SPACE to lock.

RED SCREEN (Bottom Limit): Move your sensor to the position you want to represent the "Bottom" of the screen. Press SPACE to lock.

3. Racing
Waiting at the Start Line: The game will pause at the start line. To begin the timer and start the road moving, simply make your first movement (tap an arrow key or move your sensor).

The Goal: Stay inside the white road boundaries!

Obstacles: If you loaded distract.png images, they will appear spanning the entire width of the road. Drive straight through them to burst them into sparks!

Controls: * Keyboard: Up and Down Arrow keys.

Arduino: Move your sensor to absolute positions mapped during calibration.

---

## 📂 File Structure
For the game to load your custom assets automatically, ensure your project folder looks exactly like this:

```text
/Folder
│── sahyogi.py            # The main Python script
│── pop.wav            # (Optional) Sound effect for bursting/crashing
│── player.png         # (Optional) Your custom car sprite (transparent background is best)
│── distract1.png      # (Optional) Obstacle image 1
│── distract2.png      # (Optional) Obstacle image 2
│── distract3.png      # (Optional) Obstacle image 3
└── distract4.png      # (Optional) Obstacle image 4
