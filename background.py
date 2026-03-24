# background.py — Parallax starfield + nebula with level-themed worlds

import pygame
import random
import math

# ── World theme definitions ────────────────────────────────────────────────────
WORLD_THEMES = {
    1: {
        'name': 'DEEP SPACE',
        'bg': (2, 4, 18),
        'nebula_colors': [(60, 0, 90), (0, 30, 80), (0, 60, 90)],
        'nebula_alpha': (15, 28),
        'star_tint': (255, 255, 255),
        'star_brightness': (140, 255),
        'special': None,
    },
    2: {
        'name': 'NEBULA FIELDS',
        'bg': (8, 2, 22),
        'nebula_colors': [(120, 0, 150), (0, 100, 130), (180, 30, 120), (0, 80, 160)],
        'nebula_alpha': (25, 45),
        'star_tint': (220, 200, 255),
        'star_brightness': (160, 255),
        'special': 'galaxy',
    },
    3: {
        'name': 'ASTEROID HIVE',
        'bg': (18, 8, 4),
        'nebula_colors': [(100, 40, 10), (140, 60, 20), (80, 20, 10), (120, 30, 0)],
        'nebula_alpha': (20, 38),
        'star_tint': (255, 220, 180),
        'star_brightness': (150, 230),
        'special': 'planet_red',
    },
    4: {
        'name': 'ALIEN TERRITORY',
        'bg': (2, 14, 12),
        'nebula_colors': [(0, 80, 50), (0, 60, 80), (20, 100, 40), (0, 120, 80)],
        'nebula_alpha': (20, 38),
        'star_tint': (150, 255, 180),
        'star_brightness': (140, 220),
        'special': 'bioluminescence',
    },
    5: {
        'name': 'ICE SECTOR',
        'bg': (4, 8, 30),
        'nebula_colors': [(0, 60, 140), (20, 80, 160), (40, 120, 180), (0, 40, 100)],
        'nebula_alpha': (22, 40),
        'star_tint': (180, 220, 255),
        'star_brightness': (170, 255),
        'special': 'planet_ice',
    },
    6: {
        'name': 'VOLCANIC VOID',
        'bg': (20, 5, 2),
        'nebula_colors': [(180, 40, 0), (220, 80, 0), (140, 20, 0), (200, 60, 10)],
        'nebula_alpha': (18, 35),
        'star_tint': (255, 180, 100),
        'star_brightness': (140, 220),
        'special': 'embers',
    },
    7: {
        'name': 'THE ABYSS',
        'bg': (4, 0, 8),
        'nebula_colors': [(60, 0, 60), (80, 0, 40), (40, 0, 80), (20, 0, 40)],
        'nebula_alpha': (12, 22),
        'star_tint': (200, 150, 255),
        'star_brightness': (100, 180),
        'special': 'cracks',
    },
}


# ── Star layer ─────────────────────────────────────────────────────────────────
class StarLayer:
    """A single depth-layer of stars with a tint colour."""

    def __init__(self, count: int, speed: float, size_range: tuple,
                 screen_w: int, screen_h: int,
                 tint: tuple = (255, 255, 255),
                 brightness_range: tuple = (140, 255)) -> None:
        self.speed = speed
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.tint = tint
        self.brightness_range = brightness_range
        self.stars: list = []
        for _ in range(count):
            x = random.randint(0, screen_w)
            y = random.randint(0, screen_h)
            size = random.randint(*size_range)
            brightness = random.randint(*brightness_range)
            self.stars.append([x, y, size, brightness])

    def update(self) -> None:
        for star in self.stars:
            star[0] -= self.speed
            if star[0] < 0:
                star[0] = self.screen_w
                star[1] = random.randint(0, self.screen_h)

    def draw(self, screen: pygame.Surface) -> None:
        tr, tg, tb = self.tint
        for x, y, size, brightness in self.stars:
            # Tint the star: blend brightness with tint
            t = brightness / 255.0
            col = (
                min(255, int(tr * t)),
                min(255, int(tg * t)),
                min(255, int(tb * t)),
            )
            if size == 1:
                screen.set_at((int(x), int(y)), col)
            else:
                pygame.draw.circle(screen, col, (int(x), int(y)), size)


# ── Nebula blob ───────────────────────────────────────────────────────────────
class NebulaBlob:
    """A slow-drifting coloured cloud using theme colours."""

    def __init__(self, screen_w: int, screen_h: int,
                 colors: list, alpha_range: tuple = (18, 35)) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.colors = colors
        self.alpha_range = alpha_range
        self._randomise(random.randint(0, screen_w))

    def _randomise(self, x: int) -> None:
        self.x = float(x)
        self.y = float(random.randint(50, self.screen_h - 50))
        self.radius = random.randint(60, 130)
        self.color = random.choice(self.colors)
        self.speed = random.uniform(0.05, 0.2)
        self.alpha = random.randint(*self.alpha_range)

    def update(self) -> None:
        self.x -= self.speed
        if self.x + self.radius < 0:
            self._randomise(self.screen_w + self.radius)

    def draw(self, screen: pygame.Surface) -> None:
        for scale in (1.0, 0.6):
            r = int(self.radius * scale)
            tmp = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            cr, cg, cb = self.color
            pygame.draw.circle(tmp, (cr, cg, cb, self.alpha), (r, r), r)
            screen.blit(tmp, (int(self.x) - r, int(self.y) - r))


# ── Special element: Galaxy ────────────────────────────────────────────────────
class GalaxySpecial:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.cx = int(screen_w * 0.75)
        self.cy = int(screen_h * 0.25)
        self.angle = 0.0
        self.dots = []
        # Generate spiral dots
        for i in range(120):
            t = i / 120.0
            arm = i % 2
            a = t * math.pi * 4 + arm * math.pi
            dist = 20 + t * 80
            self.dots.append((
                dist * math.cos(a),
                dist * math.sin(a) * 0.5,
                random.randint(60, 140),
            ))

    def update(self) -> None:
        self.angle += 0.003

    def draw(self, screen: pygame.Surface) -> None:
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        for dx, dy, bright in self.dots:
            rx = dx * cos_a - dy * sin_a
            ry = dx * sin_a + dy * cos_a
            sx = int(self.cx + rx)
            sy = int(self.cy + ry)
            if 0 <= sx < screen.get_width() and 0 <= sy < screen.get_height():
                col = (bright // 3, bright // 4, bright)
                screen.set_at((sx, sy), col)


# ── Special element: Red Planet ────────────────────────────────────────────────
class PlanetRedSpecial:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.cx = screen_w - 80
        self.cy = 100
        self.radius = 55

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        r = self.radius
        cx, cy = self.cx, self.cy
        # Planet body
        tmp = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (120, 45, 18, 200), (r + 2, r + 2), r)
        # Highlight
        pygame.draw.circle(tmp, (160, 70, 30, 120), (r - 8, r - 8), r // 2)
        # Ring arc (thin ellipse)
        ring_rect = pygame.Rect(2, r - 6, r * 2, 14)
        pygame.draw.ellipse(tmp, (180, 90, 40, 60), ring_rect, 3)
        screen.blit(tmp, (cx - r - 2, cy - r - 2))


# ── Special element: Ice Planet ────────────────────────────────────────────────
class PlanetIceSpecial:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.cx = screen_w - 70
        self.cy = screen_h - 90
        self.radius = 50

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        r = self.radius
        cx, cy = self.cx, self.cy
        tmp = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        # Planet body — blue-white
        pygame.draw.circle(tmp, (100, 160, 220, 200), (r + 2, r + 2), r)
        # Polar cap (white arc at top)
        pygame.draw.circle(tmp, (230, 245, 255, 180), (r + 2, r + 2 - r + 12), r // 3)
        # Slight highlight
        pygame.draw.circle(tmp, (200, 230, 255, 80), (r - 5, r - 5), r // 3)
        screen.blit(tmp, (cx - r - 2, cy - r - 2))


# ── Special element: Bioluminescence ──────────────────────────────────────────
class BioluminescenceSpecial:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.dots = []
        for _ in range(40):
            self.dots.append([
                random.uniform(0, screen_w),
                random.uniform(0, screen_h),
                random.uniform(0.1, 0.4),   # speed
                random.uniform(0, math.pi * 2),  # phase
                random.choice([(0, 255, 180), (0, 220, 255), (100, 255, 150)]),
            ])

    def update(self) -> None:
        for dot in self.dots:
            dot[1] -= dot[2]
            dot[3] += 0.04
            if dot[1] < -5:
                dot[1] = self.screen_h + 5
                dot[0] = random.uniform(0, self.screen_w)

    def draw(self, screen: pygame.Surface) -> None:
        for dot in self.dots:
            brightness = int(100 + 80 * math.sin(dot[3]))
            col = dot[4]
            alpha = brightness
            tmp = pygame.Surface((6, 6), pygame.SRCALPHA)
            r, g, b = col
            pygame.draw.circle(tmp, (r, g, b, alpha), (3, 3), 2)
            screen.blit(tmp, (int(dot[0]) - 3, int(dot[1]) - 3))


# ── Special element: Embers ───────────────────────────────────────────────────
class EmbersSpecial:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.particles = []
        for _ in range(50):
            self.particles.append([
                random.uniform(0, screen_w),
                random.uniform(0, screen_h),
                random.uniform(0.2, 0.8),   # speed upward
                random.uniform(0, math.pi * 2),  # phase
                random.choice([(255, 80, 0), (255, 140, 0), (200, 40, 0)]),
            ])

    def update(self) -> None:
        for p in self.particles:
            p[1] -= p[2]
            p[3] += 0.05
            # Slight horizontal drift
            p[0] += math.sin(p[3]) * 0.3
            if p[1] < -5:
                p[1] = self.screen_h + 5
                p[0] = random.uniform(0, self.screen_w)

    def draw(self, screen: pygame.Surface) -> None:
        for p in self.particles:
            alpha = int(100 + 60 * math.sin(p[3]))
            col = p[4]
            tmp = pygame.Surface((5, 5), pygame.SRCALPHA)
            r, g, b = col
            pygame.draw.circle(tmp, (r, g, b, alpha), (2, 2), 2)
            screen.blit(tmp, (int(p[0]) - 2, int(p[1]) - 2))


# ── Special element: Cracks ───────────────────────────────────────────────────
class CracksSpecial:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        # Generate static lightning-bolt crack lines
        self.lines = []
        for _ in range(8):
            x = random.randint(50, screen_w - 50)
            y = random.randint(50, screen_h - 50)
            pts = [(x, y)]
            cx2, cy2 = x, y
            for _ in range(random.randint(4, 8)):
                cx2 += random.randint(-40, 40)
                cy2 += random.randint(-30, 30)
                pts.append((cx2, cy2))
            self.lines.append(pts)

    def update(self) -> None:
        pass  # Static

    def draw(self, screen: pygame.Surface) -> None:
        tmp = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        for pts in self.lines:
            if len(pts) >= 2:
                for i in range(len(pts) - 1):
                    pygame.draw.line(tmp, (120, 0, 0, 35),
                                     pts[i], pts[i + 1], 1)
        screen.blit(tmp, (0, 0))


# ── Background class ──────────────────────────────────────────────────────────
class Background:
    """Manages all background layers with level-themed visuals."""

    def __init__(self, screen_w: int = 800, screen_h: int = 600,
                 level: int = 1) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.level = max(1, min(7, level))
        self._build_theme()

    def _build_theme(self) -> None:
        """Rebuild all visual elements for the current level theme."""
        theme = WORLD_THEMES.get(self.level, WORLD_THEMES[1])
        self.bg_color = theme['bg']
        star_tint = theme['star_tint']
        star_bright = theme['star_brightness']

        # Three star layers
        self.layers = [
            StarLayer(80, 0.3, (1, 1), self.screen_w, self.screen_h,
                      star_tint, star_bright),
            StarLayer(50, 0.8, (1, 2), self.screen_w, self.screen_h,
                      star_tint, star_bright),
            StarLayer(30, 1.8, (1, 2), self.screen_w, self.screen_h,
                      star_tint, star_bright),
        ]

        # 6–8 nebula blobs
        n_blobs = random.randint(6, 8)
        self.nebulae = [
            NebulaBlob(self.screen_w, self.screen_h,
                       theme['nebula_colors'], theme['nebula_alpha'])
            for _ in range(n_blobs)
        ]

        # Special element
        special = theme.get('special')
        self.special = None
        if special == 'galaxy':
            self.special = GalaxySpecial(self.screen_w, self.screen_h)
        elif special == 'planet_red':
            self.special = PlanetRedSpecial(self.screen_w, self.screen_h)
        elif special == 'planet_ice':
            self.special = PlanetIceSpecial(self.screen_w, self.screen_h)
        elif special == 'bioluminescence':
            self.special = BioluminescenceSpecial(self.screen_w, self.screen_h)
        elif special == 'embers':
            self.special = EmbersSpecial(self.screen_w, self.screen_h)
        elif special == 'cracks':
            self.special = CracksSpecial(self.screen_w, self.screen_h)

    def set_level(self, level: int) -> None:
        """Switch to a new level theme immediately."""
        self.level = max(1, min(7, level))
        self._build_theme()

    def update(self) -> None:
        for layer in self.layers:
            layer.update()
        for neb in self.nebulae:
            neb.update()
        if self.special is not None:
            self.special.update()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(self.bg_color)
        # Specials behind nebulae (e.g. planets, galaxy)
        if self.special is not None and not isinstance(
                self.special, (BioluminescenceSpecial, EmbersSpecial, CracksSpecial)):
            self.special.draw(screen)
        # Nebulae
        for neb in self.nebulae:
            neb.draw(screen)
        # Particle / overlay specials on top of nebulae but behind stars
        if self.special is not None and isinstance(
                self.special, (BioluminescenceSpecial, EmbersSpecial, CracksSpecial)):
            self.special.draw(screen)
        # Stars on top
        for layer in self.layers:
            layer.draw(screen)
