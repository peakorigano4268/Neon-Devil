import pygame
import sys
import random
import math
import io
import wave
import struct

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 900, 500
screen_real = pygame.display.set_mode((WIDTH, HEIGHT))
screen = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("Project Blood Neon: System Breach")
clock = pygame.time.Clock()

# --- MATURE SYNTHWAVE PALETTE ---
BG_COLOR, GRID_COLOR, BLACK, WHITE = (8, 2, 12), (60, 10, 20), (3, 3, 5), (220, 220, 230)
CYAN, MAGENTA, NEON_RED, YELLOW = (0, 255, 255), (180, 0, 80), (255, 10, 30), (255, 200, 0)
LIME, ORANGE, GOLD = (50, 255, 50), (255, 100, 0), (255, 215, 0)
BLOOD_COLORS = [(200, 0, 0), (150, 0, 0), (100, 0, 10), (255, 10, 30)]

# --- FONTS ---
try:
    shout_font = pygame.font.SysFont("impact", 140, bold=True)
    title_font = pygame.font.SysFont("impact", 65, bold=False)
    menu_font = pygame.font.SysFont("courier new", 24, bold=True)
    small_font = pygame.font.SysFont("courier new", 16, bold=True)
except:
    shout_font = pygame.font.Font(None, 150)
    title_font, menu_font, small_font = pygame.font.Font(None, 70), pygame.font.Font(None, 35), pygame.font.Font(None, 24)

# --- SOUND ENGINE ---
def generate_sound(stype):
    try:
        sr = 44100; buf = io.BytesIO()
        with wave.open(buf, 'w') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(sr)
            if stype == "jump":
                dur = 0.15
                for i in range(int(sr*dur)):
                    t = i/sr; f = 300+(t/dur)*600; v = int(math.sin(2*math.pi*f*t)*8000*(1-t/dur))
                    wav.writeframesraw(struct.pack('<h', max(-32768, min(32767, v))))
            elif stype == "dash":
                dur = 0.2
                for i in range(int(sr*dur)):
                    v = int((random.uniform(-1,1)*8000)*(1-i/sr/dur))
                    wav.writeframesraw(struct.pack('<h', max(-32768, min(32767, v))))
            elif stype == "death":
                dur = 0.8
                for i in range(int(sr*dur)):
                    t = i/sr; f = 100-(t/dur)*80
                    v = int(((i%max(1,int(sr/f)))>(sr/(f*2)))*20000*(1-t/dur))
                    wav.writeframesraw(struct.pack('<h', max(-32768, min(32767, v))))
            elif stype == "you_died": 
                dur = 1.2
                for i in range(int(sr*dur)):
                    t = i/sr
                    if 0.0 < t < 0.4: 
                        f = 400 - (t/0.4)*200
                        v = int(math.sin(2*math.pi*f*t) * 32767)
                        v = 32767 if v > 10000 else (-32767 if v < -10000 else v) 
                    elif 0.5 < t < 1.1: 
                        tt = t - 0.5; f = 300 - (tt/0.6)*250
                        noise = random.randint(-15000, 15000)
                        v = int(math.sin(2*math.pi*f*tt) * 32767) + noise
                        v = max(-32767, min(32767, v))
                    else: v = 0
                    wav.writeframesraw(struct.pack('<h', int(v)))
            elif stype == "win":
                dur = 1.2
                for i in range(int(sr*dur)):
                    t = i/sr; f = 330 if t<0.2 else (440 if t<0.4 else (554 if t<0.6 else 659))
                    v = int(math.sin(2*math.pi*f*t)*8000*(1-t/dur))
                    wav.writeframesraw(struct.pack('<h', max(-32768, min(32767, v))))
        buf.seek(0)
        return pygame.mixer.Sound(buf)
    except: return None

snd_jump, snd_dash, snd_death = generate_sound("jump"), generate_sound("dash"), generate_sound("death")
snd_you_died, snd_win = generate_sound("you_died"), generate_sound("win")

def play_sound(snd):
    if snd:
        try: snd.play()
        except: pass

# --- VISUAL EFFECTS ---
crt_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for y in range(0, HEIGHT, 3): pygame.draw.line(crt_overlay, (0, 0, 0, 80), (0, y), (WIDTH, y))

vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for i in range(250): pygame.draw.rect(vignette, (0, 0, 0, int(220*(1-(i/250))**1.8)), (i, i, WIDTH-i*2, HEIGHT-i*2), 1)

shake_amount, grid_offset, cheat_clicks = 0, 0, []
particles, blood_splatters = [], []

def add_particles(x, y, colors, amount, speed_mul=1.0, life=8, is_blood=False):
    for _ in range(amount):
        col = random.choice(colors) if isinstance(colors, list) else colors
        vx, vy = random.uniform(-8, 8)*speed_mul, random.uniform(-10, 5)*speed_mul
        particles.append([x, y, vx, vy, random.randint(4, life), col, is_blood])

def neon_button(text, x, y, w, h, default_col, hover_col, click_event):
    hover = x < pygame.mouse.get_pos()[0] < x+w and y < pygame.mouse.get_pos()[1] < y+h
    color, offset = (hover_col, -3) if hover else (default_col, 0)
    pygame.draw.rect(screen, color, (x-2, y+offset-2, w+4, h+4), border_radius=3)
    pygame.draw.rect(screen, BG_COLOR, (x, y+offset, w, h), border_radius=2)
    txt = menu_font.render(text, True, color)
    screen.blit(txt, txt.get_rect(center=(x+w//2, y+offset+h//2)))
    return hover and click_event

# --- CYBER-ASSASSIN PLAYER ---
class StickmanPlayer:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 40)
        self.vel_x, self.vel_y = 0, 0
        self.speed, self.friction, self.gravity, self.jump_power = 1.2, 0.8, 0.45, -10.5 
        
        self.coyote_timer, self.jump_buffer = 0, 0
        self.is_wall_sliding, self.wall_dir = False, 0
        self.dash_cooldown, self.dash_timer = 0, 0
        
        self.max_jumps, self.jumps_done = 1, 0
        self.heli_timer = 0
        self.facing_right, self.walk_cycle, self.god_mode = True, 0, False

    def update(self, keys, platforms):
        if self.god_mode:
            self.vel_x = self.vel_y = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.vel_x = -5; self.facing_right = False
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vel_x = 5; self.facing_right = True
            if keys[pygame.K_UP] or keys[pygame.K_w]: self.vel_y = -5
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.vel_y = 5
            self.rect.x += self.vel_x; self.rect.y += self.vel_y
            return

        if self.coyote_timer > 0: self.coyote_timer -= 1
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if self.dash_cooldown > 0: self.dash_cooldown -= 1
        
        if self.dash_timer > 0:
            self.vel_y = 0; self.dash_timer -= 1
            self.rect.x += self.vel_x
            add_particles(self.rect.centerx, self.rect.centery, NEON_RED, 1, 0.2)
            self.handle_collisions_x(platforms)
            return

        if self.heli_timer > 0:
            self.heli_timer -= 1
            if keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]:
                self.vel_y = -4 
                if random.random() < 0.5: add_particles(self.rect.centerx, self.rect.top, ORANGE, 1, 0.3)

        acc_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: acc_x = -self.speed; self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: acc_x = self.speed; self.facing_right = True

        if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and self.dash_cooldown == 0:
            self.vel_x = 18 if self.facing_right else -18
            self.dash_timer, self.dash_cooldown = 8, 45 
            play_sound(snd_dash)
            return

        self.vel_x = (self.vel_x + acc_x) * self.friction
        self.rect.x += self.vel_x
        self.handle_collisions_x(platforms)

        self.vel_y += self.gravity
        self.is_wall_sliding = False
        if (keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]) and self.vel_y > 0 and self.coyote_timer == 0:
            test_rect = self.rect.copy(); test_rect.x += 2 if self.facing_right else -2
            for p in platforms:
                if test_rect.colliderect(p):
                    self.is_wall_sliding = True; self.wall_dir = -1 if self.facing_right else 1
                    self.vel_y = min(self.vel_y, 2.0)
                    if random.random() < 0.3: add_particles(self.rect.centerx, self.rect.bottom, WHITE, 1, 0.5)

        self.rect.y += self.vel_y
        on_ground = self.handle_collisions_y(platforms)
        
        if on_ground: self.coyote_timer, self.is_wall_sliding, self.jumps_done = 12, False, 0 
            
        if self.jump_buffer > 0:
            if self.coyote_timer > 0: self.do_jump()
            elif self.is_wall_sliding: self.do_wall_jump()
            elif self.jumps_done < self.max_jumps: self.do_jump()

        if abs(self.vel_x) > 0.5 and on_ground: self.walk_cycle += abs(self.vel_x) * 0.2
        else: self.walk_cycle = 0

    def handle_collisions_x(self, platforms):
        for p in platforms:
            if self.rect.colliderect(p):
                self.rect.right = p.left if self.vel_x > 0 else self.rect.right
                self.rect.left = p.right if self.vel_x < 0 else self.rect.left
                self.vel_x = 0

    def handle_collisions_y(self, platforms):
        on_ground = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_y > 0: self.rect.bottom = p.top; on_ground = True
                elif self.vel_y < 0: self.rect.top = p.bottom
                self.vel_y = 0
        return on_ground

    def try_jump(self): self.jump_buffer = 12 

    def do_jump(self):
        self.vel_y = self.jump_power; self.jumps_done += 1; self.coyote_timer = self.jump_buffer = 0
        add_particles(self.rect.centerx, self.rect.bottom, NEON_RED if self.jumps_done > 1 else WHITE, 5)
        play_sound(snd_jump)

    def do_wall_jump(self):
        self.vel_y, self.vel_x = self.jump_power, self.wall_dir * 12
        self.jump_buffer, self.is_wall_sliding = 0, False
        add_particles(self.rect.centerx, self.rect.centery, WHITE, 8)
        play_sound(snd_jump); self.facing_right = (self.vel_x > 0)

    def draw(self, surface):
        x, y = self.rect.centerx, self.rect.y
        color = GOLD if self.god_mode else WHITE

        pygame.draw.rect(surface, color, (x - 8, y, 16, 16), 2)
        dir_mult = 1 if self.facing_right else -1
        pygame.draw.line(surface, NEON_RED, (x + (2 * dir_mult), y + 6), (x + (8 * dir_mult), y + 10), 3)

        body_b = y + 28
        pygame.draw.line(surface, color, (x, y + 16), (x, body_b), 2)
        swing = (5 if self.is_wall_sliding else math.sin(self.walk_cycle) * 10) * dir_mult
        
        pygame.draw.line(surface, color, (x, y + 19), (x - swing, y + 28), 2)
        pygame.draw.line(surface, color, (x, y + 19), (x + swing, y + 28), 2)
        pygame.draw.line(surface, color, (x, body_b), (x - swing, y + 38), 2)
        pygame.draw.line(surface, color, (x, body_b), (x + swing, y + 38), 2)

        if self.heli_timer > 0:
            pygame.draw.line(surface, ORANGE, (x, y), (x, y-8), 2)
            prop_spin = math.cos(pygame.time.get_ticks() * 0.05) * 14
            pygame.draw.line(surface, ORANGE, (x - prop_spin, y-8), (x + prop_spin, y-8), 3)

# --- LEVEL DESIGN ENGINE ---
def make_level(p, f_p, traps, items, moving, goal):
    return {"platforms": p, "falling_platforms": f_p, "traps": traps, "items": items, "moving": moving, "goal": goal}

levels = [
    # Level 1
    make_level([pygame.Rect(0, 450, 300, 50), pygame.Rect(550, 450, 350, 100)],
               [{"rect": pygame.Rect(300, 450, 250, 20), "timer": 0, "falling": False}], 
               [pygame.Rect(0, 480, 900, 20)], [], [], 
               {"rect": pygame.Rect(800, 340, 50, 60), "axis": None, "speed": 0, "min": 0, "max": 0}),

    # Level 2
    make_level([pygame.Rect(0, 400, 200, 100), pygame.Rect(650, 400, 250, 100)], 
               [{"rect": pygame.Rect(300, 450, 100, 20), "timer": 0, "falling": False},
                {"rect": pygame.Rect(450, 400, 100, 20), "timer": 0, "falling": False}], 
               [pygame.Rect(0, 480, 900, 20), pygame.Rect(350, 0, 200, 20)], 
               [{"rect": pygame.Rect(380, 250, 20, 20), "type": "double_jump", "collected": False}], [], 
               {"rect": pygame.Rect(800, 340, 50, 60), "axis": "x", "speed": 2, "min": 680, "max": 830}),

    # Level 3
    make_level([pygame.Rect(0, 450, 200, 50), pygame.Rect(400, 150, 50, 350), pygame.Rect(700, 450, 200, 50)],
               [{"rect": pygame.Rect(200, 350, 60, 20), "timer": 0, "falling": False},
                {"rect": pygame.Rect(600, 250, 60, 20), "timer": 0, "falling": False}],
               [pygame.Rect(0, 480, 900, 20), pygame.Rect(380, 150, 20, 350)], 
               [{"rect": pygame.Rect(220, 310, 20, 20), "type": "double_jump", "collected": False}], [], 
               {"rect": pygame.Rect(800, 390, 50, 60), "axis": "y", "speed": 3, "min": 250, "max": 400}),

    # Level 4
    make_level([pygame.Rect(0, 450, 200, 50), pygame.Rect(700, 450, 200, 50)], 
               [{"rect": pygame.Rect(350, 250, 80, 20), "timer": 0, "falling": False}], 
               [pygame.Rect(200, 480, 500, 20), pygame.Rect(200, 0, 500, 20)], 
               [{"rect": pygame.Rect(100, 390, 20, 20), "type": "helicopter", "collected": False}], [], 
               {"rect": pygame.Rect(800, 390, 50, 60), "axis": "y", "speed": 4, "min": 100, "max": 390}),

    # Level 5
    make_level([pygame.Rect(0, 400, 100, 100), pygame.Rect(800, 300, 100, 200)], 
               [{"rect": pygame.Rect(200, 300, 40, 20), "timer": 0, "falling": False},
                {"rect": pygame.Rect(400, 200, 40, 20), "timer": 0, "falling": False},
                {"rect": pygame.Rect(600, 100, 40, 20), "timer": 0, "falling": False}],
               [pygame.Rect(100, 480, 800, 20), pygame.Rect(0, 0, 900, 20), pygame.Rect(200, 320, 40, 180), pygame.Rect(400, 220, 40, 260)],
               [{"rect": pygame.Rect(150, 250, 20, 20), "type": "double_jump", "collected": False}],
               [{"rect": pygame.Rect(150, 250, 20, 150), "axis": "x", "speed": 8, "min": 150, "max": 750},
                {"rect": pygame.Rect(500, 50, 20, 200), "axis": "y", "speed": 9, "min": 50, "max": 450}], 
               {"rect": pygame.Rect(820, 240, 50, 60), "axis": "y", "speed": 12, "min": 100, "max": 400}),

    # Level 6 - NEON SPIRE
    make_level([
        pygame.Rect(0, 450, 150, 50), pygame.Rect(250, 350, 120, 30),
        pygame.Rect(450, 250, 100, 30), pygame.Rect(650, 180, 150, 30)
    ],
    [{"rect": pygame.Rect(180, 420, 60, 20), "timer": 0, "falling": False},
     {"rect": pygame.Rect(520, 300, 70, 20), "timer": 0, "falling": False}],
    [pygame.Rect(0, 480, 900, 20), pygame.Rect(300, 100, 40, 300)],
    [{"rect": pygame.Rect(300, 300, 20, 20), "type": "double_jump", "collected": False}],
    [{"rect": pygame.Rect(400, 200, 25, 180), "axis": "y", "speed": 7, "min": 120, "max": 380}],
    {"rect": pygame.Rect(820, 120, 50, 60), "axis": "y", "speed": 5, "min": 80, "max": 420}),

    # Level 7 - BLOOD CANYON
    make_level([
        pygame.Rect(0, 420, 180, 80), pygame.Rect(300, 300, 80, 30),
        pygame.Rect(500, 380, 120, 50), pygame.Rect(720, 220, 100, 40)
    ],
    [{"rect": pygame.Rect(220, 380, 70, 20), "timer": 0, "falling": False},
     {"rect": pygame.Rect(580, 280, 90, 20), "timer": 0, "falling": False}],
    [pygame.Rect(0, 480, 900, 20), pygame.Rect(150, 0, 180, 20), pygame.Rect(550, 0, 200, 20)],
    [{"rect": pygame.Rect(380, 240, 20, 20), "type": "helicopter", "collected": False}],
    [{"rect": pygame.Rect(200, 250, 30, 200), "axis": "x", "speed": 10, "min": 180, "max": 520},
     {"rect": pygame.Rect(650, 150, 25, 250), "axis": "y", "speed": 11, "min": 100, "max": 400}],
    {"rect": pygame.Rect(810, 150, 50, 60), "axis": None, "speed": 0, "min": 0, "max": 0}),

    # Level 8 - VOID ASCENT
    make_level([
        pygame.Rect(0, 450, 120, 50), pygame.Rect(180, 320, 80, 30),
        pygame.Rect(350, 220, 90, 30), pygame.Rect(520, 140, 70, 30),
        pygame.Rect(720, 80, 100, 30)
    ],
    [{"rect": pygame.Rect(100, 400, 60, 20), "timer": 0, "falling": False},
     {"rect": pygame.Rect(420, 280, 50, 20), "timer": 0, "falling": False},
     {"rect": pygame.Rect(650, 180, 55, 20), "timer": 0, "falling": False}],
    [pygame.Rect(0, 480, 900, 20), pygame.Rect(0, 0, 900, 20)],
    [{"rect": pygame.Rect(280, 280, 20, 20), "type": "double_jump", "collected": False},
     {"rect": pygame.Rect(580, 180, 20, 20), "type": "helicopter", "collected": False}],
    [{"rect": pygame.Rect(250, 100, 20, 300), "axis": "y", "speed": 8, "min": 80, "max": 420}],
    {"rect": pygame.Rect(820, 50, 50, 60), "axis": "y", "speed": 6, "min": 40, "max": 380}),

    # Level 9 - FINAL PROTOCOL
    make_level([
        pygame.Rect(0, 430, 140, 70), pygame.Rect(220, 280, 100, 30),
        pygame.Rect(420, 380, 80, 40), pygame.Rect(580, 180, 110, 30),
        pygame.Rect(750, 320, 90, 50)
    ],
    [{"rect": pygame.Rect(150, 380, 55, 20), "timer": 0, "falling": False},
     {"rect": pygame.Rect(480, 250, 65, 20), "timer": 0, "falling": False},
     {"rect": pygame.Rect(680, 340, 60, 20), "timer": 0, "falling": False}],
    [pygame.Rect(0, 480, 900, 20), pygame.Rect(100, 0, 250, 20), pygame.Rect(500, 0, 300, 20),
     pygame.Rect(300, 200, 30, 220)],
    [{"rect": pygame.Rect(350, 220, 20, 20), "type": "double_jump", "collected": False},
     {"rect": pygame.Rect(620, 140, 20, 20), "type": "helicopter", "collected": False}],
    [{"rect": pygame.Rect(180, 150, 25, 280), "axis": "x", "speed": 12, "min": 140, "max": 620},
     {"rect": pygame.Rect(520, 80, 30, 220), "axis": "y", "speed": 13, "min": 60, "max": 380}],
    {"rect": pygame.Rect(830, 80, 50, 60), "axis": "y", "speed": 15, "min": 50, "max": 420})
]

# --- GLOBALS AND MENU VARIABLES ---
player = StickmanPlayer(50, 380)
state = "BOOT"
boot_timer, death_timer = 0, 0
level_data = {}

player_name = ""
typing_name = False
diff_options = ["EASY", "NORMAL", "NIGHTMARE"]
diff_idx = 1
selected_level = 0
max_level_reached = 0

def load_level():
    global level_data
    lvl = levels[selected_level % len(levels)]
    
    # Apply Difficulty Modifiers
    diff_multiplier = 0.6 if diff_idx == 0 else (1.5 if diff_idx == 2 else 1.0)
    
    level_data = {
        "platforms": lvl["platforms"].copy(),
        "falling_platforms": [{"rect": fp["rect"].copy(), "timer": 0, "falling": False} for fp in lvl["falling_platforms"]],
        "traps": [t.copy() for t in lvl["traps"]],
        "items": [i.copy() for i in lvl["items"]],
        "moving": [{"rect": m["rect"].copy(), "axis": m["axis"], "speed": m["speed"] * diff_multiplier, "min": m["min"], "max": m["max"]} for m in lvl["moving"]],
        "goal": {"rect": lvl["goal"]["rect"].copy(), "axis": lvl["goal"]["axis"], "speed": lvl["goal"]["speed"] * diff_multiplier, "min": lvl["goal"]["min"], "max": lvl["goal"]["max"]}
    }
    player.rect.x, player.rect.y = 50, lvl["platforms"][0].top - 40
    player.vel_x = player.vel_y = player.dash_timer = player.heli_timer = player.jumps_done = 0
    player.max_jumps = 1; player.facing_right = True
    particles.clear(); blood_splatters.clear()

def trigger_death():
    global state, death_timer, shake_amount
    if player.god_mode: return 
    state, death_timer, shake_amount = "DEATH", 180, 80 
    
    play_sound(snd_death)
    play_sound(snd_you_died) 
    
    add_particles(player.rect.centerx, player.rect.centery, BLOOD_COLORS, 250, 4.0, 25, True)
    add_particles(player.rect.centerx, player.rect.centery, WHITE, 20, 5.0, 10, False)

def draw_spiky_hazard(surface, rect):
    pygame.draw.rect(surface, NEON_RED, rect); pygame.draw.rect(surface, BLOOD_COLORS[2], rect.inflate(-4, -4))
    if rect.width > rect.height:
        for i in range(rect.left, rect.right, 15):
            point_y = rect.top - 12 if rect.y > HEIGHT//2 else rect.bottom + 12
            base_y = rect.top if rect.y > HEIGHT//2 else rect.bottom
            pygame.draw.polygon(surface, NEON_RED, [(i, base_y), (i+7, point_y), (min(i+15, rect.right), base_y)])
    else:
        for i in range(rect.top, rect.bottom, 15):
            point_x = rect.left - 12 if rect.x < WIDTH//2 else rect.right + 12
            base_x = rect.left if rect.x < WIDTH//2 else rect.right
            pygame.draw.polygon(surface, NEON_RED, [(base_x, i), (point_x, i+7), (base_x, min(i+15, rect.bottom))])

# --- MAIN LOOP ---
while True:
    keys = pygame.key.get_pressed()
    click = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: click = True
        if event.type == pygame.KEYDOWN:
            if state == "MENU" and typing_name:
                if event.key == pygame.K_BACKSPACE: player_name = player_name[:-1]
                elif event.key == pygame.K_RETURN: typing_name = False
                elif len(player_name) < 12 and event.unicode.isprintable(): player_name += event.unicode.upper()
            
            if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP) and state == "PLAYING": player.try_jump()
            if event.key == pygame.K_6 and state == "PLAYING":
                cheat_clicks.append(pygame.time.get_ticks())
                if len(cheat_clicks) > 2: cheat_clicks.pop(0)
                if len(cheat_clicks) == 2 and cheat_clicks[1] - cheat_clicks[0] < 500:
                    player.god_mode = not player.god_mode; cheat_clicks.clear()

    screen.fill(BG_COLOR)
    grid_offset = (grid_offset + 1) % 40
    for x in range(-40, WIDTH, 40): pygame.draw.line(screen, GRID_COLOR, (x + grid_offset, 0), (x + grid_offset, HEIGHT), 2)
    for y in range(0, HEIGHT, 40): pygame.draw.line(screen, GRID_COLOR, (0, y + (grid_offset/2)), (WIDTH, y + (grid_offset/2)), 2)

    if state == "BOOT":
        boot_timer += 1
        txts = ["NEURAL LINK ESTABLISHING...", "BYPASSING MAINFRAME FIREWALL...", "WARNING: LETHAL COUNTERMEASURES ACTIVE", "EXECUTING: PROJECT BLOOD NEON", "SYSTEM BREACH INITIATED"]
        for i, t in enumerate(txts):
            if boot_timer > (i+1)*40:
                col = NEON_RED if i == 2 else (YELLOW if i == 4 else WHITE)
                screen.blit(small_font.render(t, True, col), (50, 100 + i*40))
        if boot_timer > 260: state = "MENU"

    elif state == "MENU":
        title = title_font.render("PROJECT: BLOOD NEON", True, MAGENTA)
        title_sh = title_font.render("PROJECT: BLOOD NEON", True, NEON_RED)
        screen.blit(title_sh, title_sh.get_rect(center=(WIDTH//2 + random.randint(-2,2), 50 + random.randint(-2,2))))
        screen.blit(title, title.get_rect(center=(WIDTH//2, 50)))
        
        # --- PLAYER NAME INPUT ---
        name_lbl = small_font.render("AGENT DESIGNATION:", True, WHITE)
        screen.blit(name_lbl, name_lbl.get_rect(center=(WIDTH//2, 110)))
        
        input_rect = pygame.Rect(WIDTH//2 - 125, 125, 250, 40)
        if click: typing_name = input_rect.collidepoint(pygame.mouse.get_pos())
        
        box_col = CYAN if typing_name else GRID_COLOR
        pygame.draw.rect(screen, box_col, input_rect, 2)
        
        disp_name = player_name + ("_" if typing_name and (pygame.time.get_ticks() % 1000 < 500) else "")
        if not player_name and not typing_name: disp_name = "CLICK TO TYPE"
        txt_surface = menu_font.render(disp_name, True, CYAN if player_name else MAGENTA)
        screen.blit(txt_surface, txt_surface.get_rect(center=input_rect.center))

        # --- DIFFICULTY SELECTOR ---
        diff_lbl = small_font.render("SYSTEM SECURITY LEVEL:", True, WHITE)
        screen.blit(diff_lbl, diff_lbl.get_rect(center=(WIDTH//2, 190)))
        
        if neon_button("<", WIDTH//2 - 120, 210, 30, 30, CYAN, WHITE, click): diff_idx = (diff_idx - 1) % 3
        d_col = LIME if diff_idx == 0 else (YELLOW if diff_idx == 1 else NEON_RED)
        d_txt = menu_font.render(diff_options[diff_idx], True, d_col)
        screen.blit(d_txt, d_txt.get_rect(center=(WIDTH//2, 225)))
        if neon_button(">", WIDTH//2 + 90, 210, 30, 30, CYAN, WHITE, click): diff_idx = (diff_idx + 1) % 3

        # --- ARRAY/LEVEL SELECTOR ---
        lvl_lbl = small_font.render("SELECT INFILTRATION NODE:", True, WHITE)
        screen.blit(lvl_lbl, lvl_lbl.get_rect(center=(WIDTH//2, 280)))
        
        if neon_button("<", WIDTH//2 - 120, 300, 30, 30, CYAN, WHITE, click): selected_level = max(0, selected_level - 1)
        l_col = WHITE if selected_level <= max_level_reached else GRID_COLOR
        l_txt = menu_font.render(f"NODE 0{selected_level+1}", True, l_col)
        screen.blit(l_txt, l_txt.get_rect(center=(WIDTH//2, 315)))
        if neon_button(">", WIDTH//2 + 90, 300, 30, 30, CYAN, WHITE, click): selected_level = min(len(levels)-1, selected_level + 1)

        # --- PROGRESS BAR ---
        prog_pct = int((max_level_reached / len(levels)) * 100)
        prog_lbl = small_font.render(f"MAINFRAME OVERRIDE PROGRESS: {prog_pct}%", True, WHITE)
        screen.blit(prog_lbl, prog_lbl.get_rect(center=(WIDTH//2, 370)))
        pygame.draw.rect(screen, GRID_COLOR, (WIDTH//2 - 150, 390, 300, 15), 2)
        pygame.draw.rect(screen, MAGENTA, (WIDTH//2 - 148, 392, int(296 * (prog_pct/100)), 11))

        # --- PLAY BUTTON ---
        btn_col = NEON_RED if selected_level <= max_level_reached else GRID_COLOR
        if neon_button("INITIATE BREACH", WIDTH//2 - 125, 430, 250, 50, btn_col, WHITE, click) and selected_level <= max_level_reached:
            load_level(); state = "PLAYING"

    elif state in ["PLAYING", "DEATH"]:
        if state == "PLAYING":
            active_platforms = level_data["platforms"][:]
            
            # Difficulty modified falling platform timer
            fall_thresh = 25 if diff_idx == 0 else (8 if diff_idx == 2 else 15)
            
            for fp in level_data["falling_platforms"]:
                if fp["timer"] <= fall_thresh: 
                    active_platforms.append(fp["rect"])
            
            player.update(keys, active_platforms)

            test_rect = player.rect.copy(); test_rect.y += 2
            for fp in level_data["falling_platforms"]:
                if player.vel_y >= 0 and test_rect.colliderect(fp["rect"]): fp["falling"] = True
            
            for fp in level_data["falling_platforms"]:
                if fp["falling"]:
                    fp["timer"] += 1
                    if fp["timer"] > fall_thresh: fp["rect"].y += 10 

            for item in level_data["items"]:
                if not item["collected"] and player.rect.colliderect(item["rect"]):
                    item["collected"] = True
                    play_sound(snd_win)
                    add_particles(item["rect"].centerx, item["rect"].centery, [LIME, WHITE], 25)
                    if item["type"] == "double_jump": player.max_jumps = 2
                    elif item["type"] == "helicopter": player.heli_timer = 600 
                    
            for m in level_data["moving"]:
                if m["axis"] == "x": m["rect"].x += m["speed"]
                else: m["rect"].y += m["speed"]
                if m["rect"].x < m["min"] or m["rect"].x > m["max"] or m["rect"].y < m["min"] or m["rect"].y > m["max"]: m["speed"] *= -1
                if not player.god_mode and player.rect.colliderect(m["rect"]): trigger_death()
                
            g_data = level_data["goal"]
            if g_data["axis"] == "x":
                g_data["rect"].x += g_data["speed"]
                if g_data["rect"].x < g_data["min"] or g_data["rect"].x > g_data["max"]: g_data["speed"] *= -1
            elif g_data["axis"] == "y":
                g_data["rect"].y += g_data["speed"]
                if g_data["rect"].y < g_data["min"] or g_data["rect"].y > g_data["max"]: g_data["speed"] *= -1

            if not player.god_mode:
                for t in level_data["traps"]:
                    if player.rect.colliderect(t): trigger_death()
                if player.rect.top > HEIGHT: trigger_death()

            # BEAT THE LEVEL
            if player.rect.colliderect(g_data["rect"]):
                play_sound(snd_win)
                selected_level += 1
                max_level_reached = max(max_level_reached, selected_level)
                
                if selected_level >= len(levels): state = "WIN"
                else: load_level()

        # Rendering Play State
        for p in level_data["platforms"]: 
            pygame.draw.rect(screen, MAGENTA, p, 4); pygame.draw.rect(screen, BLOOD_COLORS[2], p.inflate(-4, -4))
            
        for fp in level_data["falling_platforms"]:
            rect = fp["rect"]
            col = ORANGE if fp["timer"] > 0 else MAGENTA
            if 0 < fp["timer"] <= 15: rect = rect.move(random.randint(-3, 3), 0) 
            pygame.draw.rect(screen, col, rect, 4); pygame.draw.rect(screen, BLOOD_COLORS[2], rect.inflate(-4, -4))
        
        for sp in blood_splatters: pygame.draw.rect(screen, sp[3], (sp[0], sp[1], sp[2], sp[2]))
        for t in level_data["traps"]: draw_spiky_hazard(screen, t)
        
        for m in level_data["moving"]:
            pygame.draw.rect(screen, NEON_RED, m["rect"], border_radius=2)
            pygame.draw.line(screen, WHITE, m["rect"].topleft, m["rect"].bottomright, 3)
            pygame.draw.line(screen, WHITE, m["rect"].bottomleft, m["rect"].topright, 3)
            
        for item in level_data["items"]:
            if not item["collected"]:
                iy = item["rect"].y + math.sin(pygame.time.get_ticks() * 0.005) * 5
                ix = item["rect"].x
                if item["type"] == "double_jump": pygame.draw.polygon(screen, LIME, [(ix+10, iy), (ix, iy+20), (ix+20, iy+20)], 4)
                elif item["type"] == "helicopter": pygame.draw.circle(screen, ORANGE, (ix+10, int(iy+10)), 12, 4)

        g = level_data["goal"]["rect"]
        pygame.draw.rect(screen, YELLOW, g, 3)
        pygame.draw.line(screen, YELLOW, (g.centerx, g.top+10), (g.centerx, g.bottom-10), max(2, int(math.sin(pygame.time.get_ticks()*0.01)*6 + 6)))

        if state == "PLAYING":
            player.draw(screen)
            agent_str = player_name if player_name else "UNKNOWN"
            screen.blit(small_font.render(f"AGENT: {agent_str} | NODE: 0{selected_level+1}", True, WHITE), (10, 10))
            
            if player.heli_timer > 0: screen.blit(small_font.render(f"THRUSTER FUEL: {int(player.heli_timer/60*10)}s", True, ORANGE), (10, 35))
            elif player.max_jumps > 1: screen.blit(small_font.render("DOUBLE JUMP: ACQUIRED", True, LIME), (10, 35))
            else:
                dt = "[READY]" if player.dash_cooldown == 0 else "[RECHARGING]"
                screen.blit(small_font.render(f"DASH (SHIFT): {dt}", True, WHITE if player.dash_cooldown == 0 else NEON_RED), (10, 35))
        
        if state == "DEATH":
            if death_timer == 179: screen.fill(NEON_RED) 
            else:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((80, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                
                tx = WIDTH//2 + random.randint(-15, 15)
                ty = HEIGHT//2 + random.randint(-15, 15)
                
                shout_bg = shout_font.render("YOU DIED!!!", True, NEON_RED)
                shout_fg = shout_font.render("YOU DIED!!!", True, WHITE)
                
                screen.blit(shout_bg, shout_bg.get_rect(center=(tx + 6, ty + 6)))
                screen.blit(shout_fg, shout_fg.get_rect(center=(tx, ty)))
                
                sys_txt = menu_font.render("NEURAL LINK SEVERED", True, WHITE)
                screen.blit(sys_txt, sys_txt.get_rect(center=(WIDTH//2, HEIGHT - 80)))
            
            death_timer -= 1
            if death_timer <= 0: state = "GAMEOVER"

    elif state == "GAMEOVER":
        title = title_font.render("SYSTEM TERMINATED", True, NEON_RED)
        screen.blit(title, title.get_rect(center=(WIDTH//2, 150)))
        if neon_button("RETRY CURRENT NODE", WIDTH//2 - 150, 250, 300, 50, NEON_RED, WHITE, click):
            load_level(); state = "PLAYING"
        if neon_button("RETURN TO MENU", WIDTH//2 - 125, 320, 250, 50, CYAN, WHITE, click):
            state = "MENU"

    elif state == "WIN":
        title = title_font.render("MAINFRAME OBLITERATED", True, MAGENTA)
        screen.blit(title, title.get_rect(center=(WIDTH//2, 150)))
        if random.random() < 0.3: add_particles(random.randint(0, WIDTH), HEIGHT, [MAGENTA, CYAN], 3, 2.0)
        if neon_button("RETURN TO MENU", WIDTH//2 - 125, 300, 250, 50, MAGENTA, WHITE, click):
            boot_timer = 0; state = "MENU"

    # Process Particles & Blood Physics
    for p in particles[:]:
        if p[4] <= 0: 
            particles.remove(p); continue
        p[0] += p[2]; p[1] += p[3]; p[3] += 0.4 
        
        if p[6]: 
            rect = pygame.Rect(int(p[0]), int(p[1]), int(p[4]), int(p[4]))
            hit = False
            if state in ["PLAYING", "DEATH"]:
                for plat in level_data["platforms"]:
                    if rect.colliderect(plat):
                        blood_splatters.append((p[0], p[1], p[4], p[5]))
                        hit = True; break
            if hit: particles.remove(p); continue

        p[4] -= 0.15 
        pygame.draw.rect(screen, p[5], (int(p[0]), int(p[1]), int(p[4]), int(p[4])))

    screen.blit(vignette, (0,0)); screen.blit(crt_overlay, (0,0))
    
    ox = random.randint(-int(shake_amount), int(shake_amount)) if shake_amount > 0 else 0
    oy = random.randint(-int(shake_amount), int(shake_amount)) if shake_amount > 0 else 0
    if shake_amount > 0: shake_amount -= 1

    screen_real.fill(BLACK); screen_real.blit(screen, (ox, oy))
    pygame.display.flip(); clock.tick(60)