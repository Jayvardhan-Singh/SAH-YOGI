import pygame
import sys
import math
import time
import os
import random

# Safely import serial so the game runs even if pyserial isn't installed
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# --- Initialize Pygame & Audio ---
pygame.init()
pygame.mixer.init()

# --- Constants ---
WIDTH, HEIGHT = 800, 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 120, 255)
DARK_BLUE = (0, 0, 150)
DARK_RED = (150, 0, 0)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (200, 200, 200)
GREEN = (50, 200, 50)
RED = (200, 50, 50)
YELLOW = (255, 255, 0)

# Game Physics / Scaling
PIXELS_PER_SECOND = 150  
ROAD_THICKNESS = 160     

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SAHYOGI")
font = pygame.font.SysFont(None, 28)
small_font = pygame.font.SysFont(None, 22)
large_font = pygame.font.SysFont(None, 48)

# --- Asset Loader Helper ---
def load_image_safely(filename, size):
    if os.path.exists(filename):
        try:
            img = pygame.image.load(filename).convert_alpha()
            return pygame.transform.scale(img, size)
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")
    return None

# --- Hardware Integration ---
def connect_arduino():
    if not SERIAL_AVAILABLE:
        print("pyserial module not found. Defaulting to Keyboard mode.")
        return None
        
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "Arduino" in p.description or "CH340" in p.description or "usbmodem" in p.description:
            try:
                ser = serial.Serial(p.device, 115200, timeout=0)
                print(f"Connected to Arduino on {p.device}")
                return ser
            except Exception as e:
                print(f"Could not connect to {p.device}: {e}")
                
    print("No Arduino detected. Falling back to Keyboard.")
    return None

def read_arduino(arduino, current_val, buffer):
    if not arduino:
        return current_val, buffer
    try:
        while arduino.in_waiting > 0:
            char = arduino.read().decode('utf-8', errors='ignore')
            if char == '\n':
                if buffer.strip().isdigit():
                    current_val = int(buffer.strip())
                buffer = ""
            else:
                buffer += char
    except Exception:
        pass 
    return current_val, buffer

def calibrate_arduino(arduino):
    if not arduino:
        return 0, 1023 
    
    clock = pygame.time.Clock()
    raw_val = 512
    buffer = ""
    val_top = 0
    val_bot = 1023
    
    # PHASE 1: TOP
    locked = False
    while not locked:
        raw_val, buffer = read_arduino(arduino, raw_val, buffer)
        screen.fill(DARK_BLUE)
        msg1 = large_font.render("CALIBRATION: TOP", True, WHITE)
        msg2 = font.render(f"Current Sensor Reading: {raw_val}", True, YELLOW)
        msg3 = font.render("Move hand to the TOP limit and press SPACE to lock.", True, WHITE)
        screen.blit(msg1, (WIDTH//2 - msg1.get_width()//2, HEIGHT//3))
        screen.blit(msg2, (WIDTH//2 - msg2.get_width()//2, HEIGHT//2))
        screen.blit(msg3, (WIDTH//2 - msg3.get_width()//2, HEIGHT//2 + 50))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                arduino.close()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                val_top = raw_val
                locked = True
        pygame.display.flip()
        clock.tick(FPS)
        
    # PHASE 2: BOTTOM
    locked = False
    pygame.time.delay(500) 
    while not locked:
        raw_val, buffer = read_arduino(arduino, raw_val, buffer)
        screen.fill(DARK_RED)
        msg1 = large_font.render("CALIBRATION: BOTTOM", True, WHITE)
        msg2 = font.render(f"Current Sensor Reading: {raw_val}", True, YELLOW)
        msg3 = font.render("Move hand to the BOTTOM limit and press SPACE to lock.", True, WHITE)
        screen.blit(msg1, (WIDTH//2 - msg1.get_width()//2, HEIGHT//3))
        screen.blit(msg2, (WIDTH//2 - msg2.get_width()//2, HEIGHT//2))
        screen.blit(msg3, (WIDTH//2 - msg3.get_width()//2, HEIGHT//2 + 50))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                arduino.close()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                val_bot = raw_val
                locked = True
        pygame.display.flip()
        clock.tick(FPS)
        
    if val_top == val_bot:
        val_bot = val_top + 1
    return val_top, val_bot

# --- UI Classes ---
class InputBox:
    def __init__(self, x, y, w, h, text='0'):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = LIGHT_GRAY
        self.color_active = BLUE
        self.color = self.color_inactive
        self.text = text
        self.txt_surface = font.render(text, True, BLACK)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if event.unicode in '0123456789.':
                        self.text += event.unicode
                self.txt_surface = font.render(self.text, True, BLACK)

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect)
        pygame.draw.rect(surface, self.color, self.rect, 2)
        surface.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 10))

# --- Road Math Functions ---
def get_road_y(x, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length):
    if x <= w_initial:
        return base_y
    x_pattern = x - w_initial
    if x_pattern >= total_pattern_length:
        return base_y
    cycle_length = w_A + w_B + w_C + w_D
    if cycle_length == 0:
        return base_y
    x_cycle = x_pattern % cycle_length
    
    if x_cycle < w_A:
        p = x_cycle / w_A if w_A > 0 else 0
        return base_y - amp * (0.5 - 0.5 * math.cos(math.pi * p))
    elif x_cycle < w_A + w_B:
        return base_y - amp
    elif x_cycle < w_A + w_B + w_C:
        p = (x_cycle - w_A - w_B) / w_C if w_C > 0 else 0
        return base_y - amp + amp * (0.5 - 0.5 * math.cos(math.pi * p))
    else:
        return base_y

def get_road_derivative(x, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length):
    dx = 1.0
    y1 = get_road_y(x - dx, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
    y2 = get_road_y(x + dx, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
    return (y2 - y1) / (2.0 * dx)

# --- Main Menu ---
def main_menu():
    box_amp = InputBox(350, 100, 80, 40, '300')
    box_A = InputBox(350, 200, 60, 40, '2')
    box_B = InputBox(420, 200, 60, 40, '1')
    box_C = InputBox(490, 200, 60, 40, '2')
    box_D = InputBox(560, 200, 60, 40, '1')
    box_cycles = InputBox(350, 300, 80, 40, '2')
    
    boxes = [box_amp, box_A, box_B, box_C, box_D, box_cycles]
    start_btn = pygame.Rect(500, 450, 150, 60)
    clock = pygame.time.Clock()

    while True:
        screen.fill(BLACK)
        screen.blit(font.render("Select the Amplitude", True, WHITE), (50, 110))
        screen.blit(small_font.render("(Max: 450)", True, LIGHT_GRAY), (440, 112))
        screen.blit(font.render("Choose the Duration (Seconds)", True, WHITE), (50, 210))
        screen.blit(small_font.render("(Max: 10s each)", True, LIGHT_GRAY), (50, 240))
        screen.blit(font.render("A", True, WHITE), (370, 175))
        screen.blit(font.render("B", True, WHITE), (440, 175))
        screen.blit(font.render("C", True, WHITE), (510, 175))
        screen.blit(font.render("D", True, WHITE), (580, 175))
        screen.blit(font.render("Choose the Number of Cycles:", True, WHITE), (50, 310))
        
        pygame.draw.rect(screen, WHITE, start_btn)
        start_text = font.render("START", True, BLACK)
        screen.blit(start_text, (start_btn.x + 40, start_btn.y + 20))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            for box in boxes:
                box.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_btn.collidepoint(event.pos):
                    try:
                        amp = max(0.0, min(float(box_amp.text), 450.0))
                        d_A = max(0.0, min(float(box_A.text), 10.0))
                        d_B = max(0.0, min(float(box_B.text), 10.0))
                        d_C = max(0.0, min(float(box_C.text), 10.0))
                        d_D = max(0.0, min(float(box_D.text), 10.0))
                        cycles = max(1, int(box_cycles.text))
                        return amp, d_A, d_B, d_C, d_D, cycles
                    except ValueError:
                        print("Please enter valid numbers.")

        for box in boxes:
            box.draw(screen)
        pygame.display.flip()
        clock.tick(30)

def play_game(amp, d_A, d_B, d_C, d_D, cycles, arduino, val_top, val_bot):
    # --- LOAD AUDIO ---
    pop_sound = None
    if os.path.exists("pop.wav"):
        try:
            pop_sound = pygame.mixer.Sound("pop.wav")
        except Exception as e:
            print(f"Warning: Could not load pop.wav: {e}")

    # --- LOAD ASSETS DYNAMICALLY ---
    car_size = 30
    player_img = load_image_safely("player.png", (car_size, car_size))
    
    # Load all available distraction images
    distract_size = ROAD_THICKNESS - 40 
    available_distract_imgs = []
    for i in range(1, 5):
        d_img = load_image_safely(f"distract{i}.png", (distract_size, distract_size)) 
        if d_img:
            available_distract_imgs.append(d_img)

    w_A = d_A * PIXELS_PER_SECOND
    w_B = d_B * PIXELS_PER_SECOND
    w_C = d_C * PIXELS_PER_SECOND
    w_D = d_D * PIXELS_PER_SECOND
    
    cycle_width = w_A + w_B + w_C + w_D
    total_pattern_length = cycle_width * cycles
    
    w_initial = 2.0 * PIXELS_PER_SECOND 
    w_final = 1.5 * PIXELS_PER_SECOND
    total_road_length = w_initial + total_pattern_length + w_final
    base_y = HEIGHT // 2 + amp // 2
    
    # --- PRE-GENERATE DISTRACTIONS ---
    # We place them exactly in the middle of segments B and D
    game_distractions = []
    if available_distract_imgs:
        for i in range(cycles):
            cycle_start = w_initial + (i * cycle_width)
            
            # Middle of Top Straight (B)
            if w_B > 0:
                mid_B_x = cycle_start + w_A + (w_B / 2)
                game_distractions.append({
                    'x': mid_B_x,
                    'img': random.choice(available_distract_imgs), # Select randomly from available pool
                    'hit': False
                })
                
            # Middle of Bottom Straight (D)
            if w_D > 0:
                mid_D_x = cycle_start + w_A + w_B + w_C + (w_D / 2)
                game_distractions.append({
                    'x': mid_D_x,
                    'img': random.choice(available_distract_imgs), # Select randomly from available pool
                    'hit': False
                })

    raw_sensor_val = val_top + (val_bot - val_top) // 2 
    serial_buffer = ""
    smoothed_sensor_val = raw_sensor_val
    smoothing_factor = 0.15 

    clock = pygame.time.Clock()
    camera_x = 0
    car_x = 150
    car_y = base_y
    initial_car_y = car_y 
    
    start_time = 0
    current_time = 0
    state = "WAITING"
    particles = []

    while True:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if arduino:
                    arduino.close()
                pygame.quit()
                sys.exit()

        if state in ["WAITING", "PLAYING"]:
            if arduino:
                raw_sensor_val, serial_buffer = read_arduino(arduino, raw_sensor_val, serial_buffer)
                smoothed_sensor_val = (smoothing_factor * raw_sensor_val) + ((1.0 - smoothing_factor) * smoothed_sensor_val)
                fraction = (smoothed_sensor_val - val_top) / (val_bot - val_top)
                target_y = fraction * HEIGHT
                target_y = max(0, min(HEIGHT, target_y)) 
                car_y += (target_y - car_y) * 15 * dt 
            else:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]: car_y -= 300 * dt
                if keys[pygame.K_DOWN]: car_y += 300 * dt

            if state == "WAITING":
                if abs(car_y - initial_car_y) > 10: 
                    state = "PLAYING"
                    start_time = time.time()
                    
            elif state == "PLAYING":
                camera_x += PIXELS_PER_SECOND * dt
                current_time = time.time() - start_time
                absolute_car_x = camera_x + car_x + car_size/2 
                car_rect = pygame.Rect(car_x, car_y - car_size//2, car_size, car_size)
                
                # 1. Check Interaction with Distractions (Burst them without crashing)
                for d in game_distractions:
                    if not d['hit']:
                        screen_x = d['x'] - camera_x
                        if -150 < screen_x < WIDTH + 150:
                            img = d['img']
                            road_y = get_road_y(d['x'], amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
                            img_y = road_y - (img.get_height() / 2)
                            distract_rect = pygame.Rect(screen_x, img_y, img.get_width(), img.get_height())
                            
                            if car_rect.colliderect(distract_rect):
                                d['hit'] = True # Mark as hit so it vanishes
                                if pop_sound:
                                    pop_sound.play()
                                    
                                # Spawn fun particles exactly where the image was
                                for _ in range(30):
                                    dx = random.uniform(-6, 6)
                                    dy = random.uniform(-6, 6)
                                    radius = random.randint(3, 8)
                                    color = (random.randint(200, 255), random.randint(150, 255), 0)
                                    particles.append([car_x + car_size//2, car_y, dx, dy, radius, color])
                
                # 2. Check Collision with Road Boundaries (Lethal)
                road_y_center = get_road_y(absolute_car_x, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
                dy_dx = get_road_derivative(absolute_car_x, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
                
                vertical_dist = abs(car_y - road_y_center)
                L = math.sqrt(1 + dy_dx**2)
                perp_dist = vertical_dist / L
                hit_wall = (perp_dist + (car_size / 2) > ROAD_THICKNESS / 2)
                
                # 3. Trigger Game Over / Win States
                if hit_wall:
                    state = "LOSE"
                    if pop_sound: 
                        pop_sound.play()
                    for _ in range(40):
                        dx = random.uniform(-6, 6)
                        dy = random.uniform(-6, 6)
                        radius = random.randint(3, 10)
                        color = (255, random.randint(50, 150), 0) 
                        particles.append([car_x + car_size//2, car_y, dx, dy, radius, color])
                        
                elif camera_x + car_x + car_size >= w_initial + total_pattern_length:
                    state = "WIN"

        # --- Update Particles ---
        for p in particles:
            p[0] += p[2] * dt * 60  
            p[1] += p[3] * dt * 60  
            p[4] -= 0.15 * dt * 60  

        # --- Drawing ---
        screen.fill(DARK_GRAY)
        
        points_upper = []
        points_lower = []
        
        for x in range(int(camera_x) - 100, int(camera_x + WIDTH + 100), 10):
            clamped_x = min(x, total_road_length)
            y = get_road_y(clamped_x, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
            dy_dx = get_road_derivative(clamped_x, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
            
            L = math.sqrt(1 + dy_dx**2)
            nx = -dy_dx / L
            ny = 1.0 / L
            
            px_upper = clamped_x - (ROAD_THICKNESS / 2) * nx
            py_upper = y - (ROAD_THICKNESS / 2) * ny
            px_lower = clamped_x + (ROAD_THICKNESS / 2) * nx
            py_lower = y + (ROAD_THICKNESS / 2) * ny
                
            points_upper.append((px_upper - camera_x, py_upper))
            points_lower.append((px_lower - camera_x, py_lower))
            
        points_lower.reverse()
        if len(points_upper) > 1:
            pygame.draw.polygon(screen, LIGHT_GRAY, points_upper + points_lower)
            pygame.draw.lines(screen, WHITE, False, points_upper, 4)
            pygame.draw.lines(screen, WHITE, False, points_lower, 4)

        # --- Draw Distractions (Only if not hit) ---
        for d in game_distractions:
            if not d['hit']:
                screen_x = d['x'] - camera_x
                if -150 < screen_x < WIDTH + 150:
                    img = d['img']
                    road_y = get_road_y(d['x'], amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
                    img_y = road_y - (img.get_height() / 2)
                    screen.blit(img, (screen_x, img_y))

        # Draw Start Line
        start_line_x = w_initial - camera_x
        if -50 < start_line_x < WIDTH + 50:
            dy_dx = get_road_derivative(w_initial, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
            L = math.sqrt(1 + dy_dx**2)
            nx, ny = -dy_dx / L, 1.0 / L
            top_pt = (start_line_x - (ROAD_THICKNESS / 2) * nx, base_y - (ROAD_THICKNESS / 2) * ny)
            bot_pt = (start_line_x + (ROAD_THICKNESS / 2) * nx, base_y + (ROAD_THICKNESS / 2) * ny)
            pygame.draw.line(screen, GREEN, top_pt, bot_pt, 8)
            screen.blit(font.render("START", True, GREEN), (top_pt[0] + 10, top_pt[1] - 20))

        # Draw Finish Line
        finish_line_x = w_initial + total_pattern_length - camera_x
        finish_y = get_road_y(w_initial + total_pattern_length, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
        if -50 < finish_line_x < WIDTH + 50:
            dy_dx = get_road_derivative(w_initial + total_pattern_length, amp, w_A, w_B, w_C, w_D, base_y, w_initial, total_pattern_length)
            L = math.sqrt(1 + dy_dx**2)
            nx, ny = -dy_dx / L, 1.0 / L
            top_pt = (finish_line_x - (ROAD_THICKNESS / 2) * nx, finish_y - (ROAD_THICKNESS / 2) * ny)
            bot_pt = (finish_line_x + (ROAD_THICKNESS / 2) * nx, finish_y + (ROAD_THICKNESS / 2) * ny)
            pygame.draw.line(screen, RED, top_pt, bot_pt, 8)
            screen.blit(font.render("FINISH", True, RED), (top_pt[0] + 10, top_pt[1] - 20))

        # --- Draw the Car or Player Image ---
        if state != "LOSE":
            if player_img:
                screen.blit(player_img, (car_x, car_y - car_size//2))
            else:
                car_rect = pygame.Rect(car_x, car_y - car_size//2, car_size, car_size)
                pygame.draw.rect(screen, BLUE, car_rect)

        # --- Draw Spark Particles ---
        for p in particles:
            if p[4] > 0: 
                pygame.draw.circle(screen, p[5], (int(p[0]), int(p[1])), int(p[4]))

        # --- Draw UI Overlays ---
        score_txt = font.render(f"Time: {current_time:.2f} s", True, WHITE if state == "PLAYING" else YELLOW)
        screen.blit(score_txt, (20, 20))
        
        if state == "WAITING":
            wait_msg = large_font.render("PRESS UP/DOWN OR HOVER HAND TO START", True, YELLOW)
            bg_rect = wait_msg.get_rect(center=(WIDTH//2, HEIGHT//3))
            pygame.draw.rect(screen, BLACK, bg_rect.inflate(20, 20))
            screen.blit(wait_msg, bg_rect)

        calib_rect = pygame.Rect(10, HEIGHT - 50, 400, 40)
        pygame.draw.rect(screen, BLACK, calib_rect)
        pygame.draw.rect(screen, WHITE, calib_rect, 2)
        
        if arduino:
            calib_text = small_font.render(f"Raw: {raw_sensor_val} | Smooth: {int(smoothed_sensor_val)} | Map: [{val_top}-{val_bot}]", True, GREEN)
        else:
            calib_text = small_font.render("Input: Keyboard (Up/Down Arrows)", True, YELLOW)
            
        screen.blit(calib_text, (20, HEIGHT - 45))

        if state == "WIN":
            msg = large_font.render("CONGRATULATIONS! YOU WIN!", True, GREEN)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))
        elif state == "LOSE":
            msg = large_font.render("CRASHED! GAME OVER", True, RED)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))

        pygame.display.flip()

        if state in ["WIN", "LOSE"]:
            pygame.time.delay(3000)
            if arduino:
                arduino.close() 
            return

# --- Main Game Loop ---
if __name__ == "__main__":
    while True:
        params = main_menu()
        arduino = connect_arduino()
        val_top, val_bot = calibrate_arduino(arduino)
        play_game(*params, arduino, val_top, val_bot)
