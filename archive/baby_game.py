"""
Baby Game
=========
A colourful, noisy, no-pressure game for babies and toddlers.

GAME MODES (pick from the menu, or press 1-4):
  1. Free Play     - any key or click makes a coloured ball with a letter on it.
                     A key says the LETTER, a click says the COLOUR.
  2. Letter Hunt   - a big letter appears and is spoken. Press that letter on the
                     keyboard to score. You can NEVER lose - wrong keys just gently
                     repeat the target.
  3. Colour Splash - big colourful splashes that say their colour name.
  4. Family Faces  - photos of family members pop up and their name is spoken.

PARENT CONTROLS (kept off the A-Z keys so they never clash with play):
  Esc        -> back to menu  (and quit from the menu)
  F11        -> toggle full screen
  Backspace  -> restart / clear the current game

ADDING FAMILY FACES:
  Put photos (.png .jpg .jpeg .bmp .gif) in the "assets/faces" folder that sits
  next to this file (it is created automatically the first time you run the game).
  The file name becomes the spoken name, e.g.  grandma.jpg -> "Grandma",
  uncle_ben.png -> "Uncle Ben".  Then open Family Faces and press any key.

REQUIREMENTS:
  pip install pygame pyttsx3
  (pyttsx3 is only needed for the talking. The game still runs without it.)

MAKING A .EXE  (Windows):
  pip install pyinstaller pygame pyttsx3
  pyinstaller --onefile --windowed --name BabyGame ^
      --hidden-import pyttsx3.drivers ^
      --hidden-import pyttsx3.drivers.sapi5 ^
      baby_game.py
  The exe appears in the "dist" folder. Create a "dist/assets/faces" folder next
  to the exe and drop your photos in there.  (On Mac/Linux replace the "^" line
  breaks with a backslash, and use pyttsx3.drivers.nsss / espeak instead of sapi5.)
"""

import os
import sys
import math
import array
import random
import queue
import threading

import pygame

# ---- optional text-to-speech (game still runs if missing) ----
try:
    import pyttsx3
    HAS_TTS = True
except Exception:
    HAS_TTS = False


def base_dir():
    """Folder the game lives in - works both as a script and as a frozen .exe."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


ASSETS = os.path.join(base_dir(), "assets")
FACES_DIR = os.path.join(ASSETS, "faces")

# Named colours so we can SAY the colour out loud.
PALETTE = [
    ("red", (231, 76, 60)),
    ("orange", (230, 126, 34)),
    ("yellow", (241, 196, 15)),
    ("green", (46, 204, 113)),
    ("blue", (52, 152, 219)),
    ("purple", (155, 89, 182)),
    ("pink", (255, 105, 180)),
    ("teal", (26, 188, 156)),
]

LETTERS_AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# game states
MENU, FREEPLAY, LETTERS, COLOURS, FACES = "menu", "free", "letters", "colours", "faces"


# ----------------------------------------------------------------------
# Speaking (runs on its own thread so the game never freezes while talking)
# ----------------------------------------------------------------------
class Speaker:
    def __init__(self, rate=150):
        self.queue = queue.Queue()
        self.ok = HAS_TTS
        if not self.ok:
            return
        self._rate = rate
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self):
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
        except Exception:
            self.ok = False
            return
        while True:
            text = self.queue.get()
            if text is None:
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass

    def say(self, text):
        if not self.ok:
            return
        # A toddler will mash keys - keep only the newest request so it stays snappy.
        try:
            while self.queue.qsize() > 1:
                self.queue.get_nowait()
        except queue.Empty:
            pass
        self.queue.put(str(text))

    def stop(self):
        if self.ok:
            self.queue.put(None)


# ----------------------------------------------------------------------
# Sound effects (generated in code, so no sound files are needed)
# ----------------------------------------------------------------------
class SoundBank:
    def __init__(self):
        self.ok = False
        self.pops = []
        self.success = None
        self.soft = None
        self._sr = 44100
        try:
            self._build()
            self.ok = True
        except Exception:
            self.ok = False

    def _tone(self, freqs, ms, volume=0.5):
        sr = self._sr
        n = int(sr * ms / 1000)
        buf = array.array("h")
        amp = 32767 * volume
        attack = max(1, int(0.01 * sr))
        release = max(1, int(0.06 * sr))
        for i in range(n):
            if i < attack:
                env = i / attack
            elif i > n - release:
                env = max(0.0, (n - i) / release)
            else:
                env = 1.0
            s = 0.0
            for f in freqs:
                s += math.sin(2 * math.pi * f * i / sr)
            s /= len(freqs)
            v = int(amp * env * s)
            buf.append(v)   # left
            buf.append(v)   # right
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _build(self):
        for f in (523, 587, 659, 784, 880):          # cheerful pops
            self.pops.append(self._tone([f], 130, 0.45))
        self.success = self._tone([523, 659, 784], 320, 0.5)   # happy C-major chord
        self.soft = self._tone([330], 150, 0.35)     # gentle neutral boop

    def pop(self):
        if self.ok and self.pops:
            random.choice(self.pops).play()

    def yay(self):
        if self.ok and self.success:
            self.success.play()

    def boop(self):
        if self.ok and self.soft:
            self.soft.play()


# ----------------------------------------------------------------------
# On-screen things
# ----------------------------------------------------------------------
class Ball:
    def __init__(self, x, y, radius, color, letter, font):
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.letter = letter
        self.font = font
        self.scale = 0.1   # little pop-in animation

    def update(self, dt):
        if self.scale < 1.0:
            self.scale = min(1.0, self.scale + dt * 6)

    def draw(self, surf):
        r = int(self.radius * self.scale)
        if r <= 0:
            return
        pygame.draw.circle(surf, self.color, (self.x, self.y), r)
        if self.letter:
            lum = 0.299 * self.color[0] + 0.587 * self.color[1] + 0.114 * self.color[2]
            tcol = (0, 0, 0) if lum > 140 else (255, 255, 255)
            img = self.font.render(self.letter, True, tcol)
            if self.scale < 1.0:
                img = pygame.transform.rotozoom(img, 0, self.scale)
            surf.blit(img, img.get_rect(center=(self.x, self.y)))


class FaceSprite:
    def __init__(self, name, img, x, y):
        self.name, self.img = name, img
        self.x, self.y = x, y
        self.scale = 0.1

    def update(self, dt):
        if self.scale < 1.0:
            self.scale = min(1.0, self.scale + dt * 5)

    def draw(self, surf):
        img = self.img
        if self.scale < 1.0:
            w = max(1, int(img.get_width() * self.scale))
            h = max(1, int(img.get_height() * self.scale))
            img = pygame.transform.smoothscale(img, (w, h))
        surf.blit(img, img.get_rect(center=(self.x, self.y)))


def circle_crop(img, size):
    """Scale a photo to fill a square, then mask it into a circle with a white ring."""
    iw, ih = img.get_size()
    scale = size / min(iw, ih)
    img = pygame.transform.smoothscale(img, (max(size, int(iw * scale)),
                                             max(size, int(ih * scale))))
    iw, ih = img.get_size()
    x = (iw - size) // 2
    y = (ih - size) // 2
    square = img.subsurface((x, y, size, size)).copy()
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    square.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.circle(square, (255, 255, 255), (size // 2, size // 2), size // 2, 6)
    return square


def load_faces():
    faces = []
    if not os.path.isdir(FACES_DIR):
        return faces
    exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
    for fn in sorted(os.listdir(FACES_DIR)):
        if not fn.lower().endswith(exts):
            continue
        try:
            img = pygame.image.load(os.path.join(FACES_DIR, fn)).convert_alpha()
            img = circle_crop(img, 220)
        except Exception:
            continue
        name = os.path.splitext(fn)[0].replace("_", " ").replace("-", " ").strip().title()
        faces.append((name, img))
    return faces


# ----------------------------------------------------------------------
# The game
# ----------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.display.set_caption("Baby Game")
        self.windowed_size = (1280, 800)
        self.fullscreen = False
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.W, self.H = self.screen.get_size()
        self.clock = pygame.time.Clock()
        self.speaker = Speaker()
        self.sounds = SoundBank()
        self.faces = load_faces()
        self.state = MENU
        self.objects = []
        self.max_objects = 40
        self.target_letter = None
        self.score = 0
        self._make_fonts()

    # ---- display helpers ----
    def _make_fonts(self):
        self.font_small = pygame.font.Font(None, 38)
        self.font_med = pygame.font.Font(None, 64)
        self.font_title = pygame.font.Font(None, 110)
        self.font_big = pygame.font.Font(None, max(200, self.H // 2))
        self.font_ball = pygame.font.Font(None, 72)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.W, self.H = self.screen.get_size()
        self._make_fonts()

    def _rand_pos(self, margin):
        x = random.randint(margin, max(margin + 1, self.W - margin))
        y = random.randint(margin, max(margin + 1, self.H - margin))
        return x, y

    def _cap(self):
        if len(self.objects) > self.max_objects:
            self.objects = self.objects[-self.max_objects:]

    # ---- mode control ----
    def start_mode(self, mode):
        self.state = mode
        self.objects = []
        self.score = 0
        if mode == LETTERS:
            self.new_target()
        elif mode == FACES:
            if self.faces:
                self.speaker.say("Family faces")
            else:
                self.speaker.say("Add photos to the faces folder")

    def go_menu(self):
        self.state = MENU
        self.objects = []

    def restart(self):
        if self.state != MENU:
            self.start_mode(self.state)

    # ---- spawning ----
    def spawn_ball(self, letter, speak, big=False, play_pop=True):
        name, color = random.choice(PALETTE)
        r = random.randint(120, 200) if big else random.randint(60, 110)
        x, y = self._rand_pos(r)
        self.objects.append(Ball(x, y, r, color, letter, self.font_ball))
        self._cap()
        if play_pop:
            self.sounds.pop()
        if speak == "letter" and letter:
            self.speaker.say(letter)
        elif speak == "colour":
            self.speaker.say(name)

    def spawn_face(self):
        if not self.faces:
            self.speaker.say("Add photos first")
            self.sounds.boop()
            return
        name, img = random.choice(self.faces)
        x, y = self._rand_pos(140)
        self.objects.append(FaceSprite(name, img, x, y))
        self._cap()
        self.sounds.pop()
        self.speaker.say(name)

    # ---- letter hunt ----
    def new_target(self):
        self.target_letter = random.choice(LETTERS_AZ)
        self.speaker.say(self.target_letter)

    def check_letter(self, ch):
        if not ch or not ch.isalpha():
            return
        if ch == self.target_letter:
            self.score += 1
            self.sounds.yay()
            self.speaker.say("Yes! " + ch)
            for _ in range(6):                      # confetti of balls
                self.spawn_ball(letter=ch, speak="none", play_pop=False)
            self.new_target()
        else:
            self.sounds.boop()
            self.speaker.say(self.target_letter)    # gently repeat - never a loss

    # ---- menu ----
    def menu_items(self):
        items = [
            ("1   Free Play", FREEPLAY),
            ("2   Letter Hunt", LETTERS),
            ("3   Colour Splash", COLOURS),
            ("4   Family Faces", FACES),
        ]
        bw, bh = min(700, self.W - 120), 88
        x = (self.W - bw) // 2
        y0 = self.H // 2 - 150
        return [(label, mode, pygame.Rect(x, y0 + i * (bh + 22), bw, bh))
                for i, (label, mode) in enumerate(items)]

    def menu_click(self, pos):
        for label, mode, rect in self.menu_items():
            if rect.collidepoint(pos):
                self.start_mode(mode)
                return

    # ---- input dispatch ----
    def on_key(self, event):
        if self.state == MENU:
            if event.unicode in "1234":
                mapping = {"1": FREEPLAY, "2": LETTERS, "3": COLOURS, "4": FACES}
                self.start_mode(mapping[event.unicode])
            return
        ch = event.unicode.upper()
        if self.state == FREEPLAY:
            self.spawn_ball(letter=ch if ch.isalnum() else random.choice(LETTERS_AZ),
                            speak="letter")
        elif self.state == COLOURS:
            self.spawn_ball(letter="", speak="colour", big=True)
        elif self.state == LETTERS:
            self.check_letter(ch)
        elif self.state == FACES:
            self.spawn_face()

    def on_click(self, pos):
        if self.state == MENU:
            self.menu_click(pos)
        elif self.state == FREEPLAY:
            self.spawn_ball(letter=random.choice(LETTERS_AZ), speak="colour")
        elif self.state == COLOURS:
            self.spawn_ball(letter="", speak="colour", big=True)
        elif self.state == LETTERS:
            if self.target_letter:                  # tap to hear it again
                self.speaker.say(self.target_letter)
                self.sounds.boop()
        elif self.state == FACES:
            self.spawn_face()

    # ---- drawing ----
    def draw(self):
        if self.state == MENU:
            self.draw_menu()
            return
        self.screen.fill((20, 20, 35))
        for o in self.objects:
            o.draw(self.screen)
        if self.state == LETTERS:
            self.draw_letters_overlay()
        if self.state == FACES and not self.faces:
            self.draw_center_text("Put photos in this folder:", FACES_DIR,
                                  "then press Backspace")
        self.draw_hint("Esc: menu     F11: full screen     Backspace: restart")

    def draw_letters_overlay(self):
        if not self.target_letter:
            return
        img = self.font_big.render(self.target_letter, True, (255, 255, 255))
        img.set_alpha(55)
        self.screen.blit(img, img.get_rect(center=(self.W // 2, self.H // 2)))
        s = self.font_med.render("Press:  " + self.target_letter, True, (255, 255, 255))
        self.screen.blit(s, s.get_rect(center=(self.W // 2, 70)))
        sc = self.font_small.render("Score: %d" % self.score, True, (241, 196, 15))
        self.screen.blit(sc, (20, self.H - 50))

    def draw_center_text(self, *lines):
        for i, line in enumerate(lines):
            s = self.font_small.render(line, True, (220, 220, 220))
            self.screen.blit(s, s.get_rect(center=(self.W // 2, self.H // 2 + i * 42)))

    def draw_hint(self, text):
        s = self.font_small.render(text, True, (150, 150, 160))
        self.screen.blit(s, (20, 20))

    def draw_menu(self):
        self.screen.fill((25, 28, 48))
        t = self.font_title.render("Baby Game", True, (255, 255, 255))
        self.screen.blit(t, t.get_rect(center=(self.W // 2, self.H // 2 - 230)))
        sub = self.font_small.render("Tap a game, or press its number", True, (170, 175, 200))
        self.screen.blit(sub, sub.get_rect(center=(self.W // 2, self.H // 2 - 175)))
        mouse = pygame.mouse.get_pos()
        for label, mode, rect in self.menu_items():
            hot = rect.collidepoint(mouse)
            pygame.draw.rect(self.screen, (70, 90, 160) if hot else (45, 55, 95),
                             rect, border_radius=18)
            pygame.draw.rect(self.screen, (120, 140, 210), rect, 3, border_radius=18)
            l = self.font_med.render(label, True, (255, 255, 255))
            self.screen.blit(l, l.get_rect(center=rect.center))
        foot = self.font_small.render("Esc: quit      F11: full screen", True, (140, 145, 170))
        self.screen.blit(foot, foot.get_rect(center=(self.W // 2, self.H - 50)))
        if not HAS_TTS:
            w = self.font_small.render("(install pyttsx3 to make it talk)", True, (200, 120, 120))
            self.screen.blit(w, w.get_rect(center=(self.W // 2, self.H - 90)))

    # ---- main loop ----
    def update(self, dt):
        for o in self.objects:
            o.update(dt)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.windowed_size = (event.w, event.h)
                    self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                    self.W, self.H = self.screen.get_size()
                    self._make_fonts()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_ESCAPE:
                        if self.state == MENU:
                            running = False
                        else:
                            self.go_menu()
                    elif event.key == pygame.K_BACKSPACE:
                        self.restart()
                    else:
                        self.on_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.on_click(event.pos)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        self.speaker.stop()
        pygame.quit()


def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass
    try:
        os.makedirs(FACES_DIR, exist_ok=True)
    except Exception:
        pass
    Game().run()


if __name__ == "__main__":
    main()
