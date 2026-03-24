# powerups.py — Power-up system

import pygame
import math
import random
from assets import (YELLOW, CYAN, PURPLE, BLUE, RED, WHITE,
                    draw_circle_alpha, draw_star_shape,
                    draw_lightning_bolt, draw_arrows, draw_cross,
                    draw_humanoid)

# Power-up type constants (positive)
SPEED_UP       = "SPEED_UP"
MULTISHOT      = "MULTISHOT"
WEAPON_UPGRADE = "WEAPON_UPGRADE"
SHADOW_CLONE   = "SHADOW_CLONE"
HEALTH_UP      = "HEALTH_UP"
BOMB           = "BOMB"             # grants one bomb (press B to detonate)

# Negative power-up type constants
REVERSE_CONTROLS = "REVERSE_CONTROLS"   # reverses WASD for 8 seconds
SPEED_DOWN       = "SPEED_DOWN"          # halves bullet speed (permanent)
SHOT_REDUCE      = "SHOT_REDUCE"         # reduces multishot count by 1
WEAPON_CURSE     = "WEAPON_CURSE"        # forces weapon back to LASER

# Pools
POSITIVE_TYPES = [SPEED_UP, MULTISHOT, WEAPON_UPGRADE, SHADOW_CLONE, HEALTH_UP, BOMB]
NEGATIVE_TYPES = [REVERSE_CONTROLS, SPEED_DOWN, SHOT_REDUCE, WEAPON_CURSE]
ALL_TYPES = POSITIVE_TYPES + NEGATIVE_TYPES

TYPE_COLORS = {
    SPEED_UP:         YELLOW,
    MULTISHOT:        CYAN,
    WEAPON_UPGRADE:   PURPLE,
    SHADOW_CLONE:     BLUE,
    HEALTH_UP:        RED,
    BOMB:             (255, 120, 0),
    # Negative types
    REVERSE_CONTROLS: (180, 0, 0),
    SPEED_DOWN:       (160, 80, 0),
    SHOT_REDUCE:      (80, 80, 80),
    WEAPON_CURSE:     (100, 0, 140),
}

TYPE_LABELS = {
    SPEED_UP:         "SPEED",
    MULTISHOT:        "MULTI",
    WEAPON_UPGRADE:   "WEAPON",
    SHADOW_CLONE:     "CLONE",
    HEALTH_UP:        "HEALTH",
    BOMB:             "BOMB",
    REVERSE_CONTROLS: "REVERSE",
    SPEED_DOWN:       "SLOW",
    SHOT_REDUCE:      "REDUCE",
    WEAPON_CURSE:     "CURSE",
}


class PowerUp:
    RADIUS       = 18
    COLLECT_DIST = 30
    ROT_SPEED    = 1.5    # degrees per frame
    BOB_SPEED    = 0.06
    BOB_AMP      = 6
    SCROLL_SPEED = 0.5    # drift left

    def __init__(self, x: float, y: float,
                 pu_type: str | None = None,
                 negative: bool = False) -> None:
        self.x = float(x)
        self.base_y = float(y)
        self.y = self.base_y
        self.pu_type = pu_type if pu_type else random.choice(ALL_TYPES)
        self.negative = negative or (self.pu_type in NEGATIVE_TYPES)
        self.angle = 0.0
        self.bob_phase = random.uniform(0, math.pi * 2)
        self._dead = False
        self.color = TYPE_COLORS[self.pu_type]
        self.lifetime = 600   # 10 seconds at 60 fps

    @property
    def dead(self) -> bool:
        return self._dead

    def update(self) -> None:
        self.angle += self.ROT_SPEED
        self.bob_phase += self.BOB_SPEED
        self.y = self.base_y + math.sin(self.bob_phase) * self.BOB_AMP
        # Scroll left
        self.x -= self.SCROLL_SPEED
        self.base_y = self.y - math.sin(self.bob_phase) * self.BOB_AMP
        # Lifetime countdown
        self.lifetime -= 1
        if self.lifetime <= 0:
            self._dead = True

    def check_collect(self, player) -> bool:
        dx = self.x - player.x
        dy = self.y - player.y
        if math.hypot(dx, dy) < self.COLLECT_DIST:
            self._dead = True
            return True
        return False

    def draw(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        r = self.RADIUS
        angle_rad = math.radians(self.angle)

        if self.negative:
            # Dark background circle
            pygame.draw.circle(screen, (40, 0, 0), (cx, cy), r)
            pygame.draw.circle(screen, self.color, (cx, cy), r, 2)
            # Pulsing red glow
            glow_alpha = int(abs(math.sin(self.bob_phase * 2)) * 60 + 20)
            draw_circle_alpha(screen, (180, 0, 0), (cx, cy), r + 8, glow_alpha)
            draw_circle_alpha(screen, (180, 0, 0), (cx, cy), r + 4, min(255, glow_alpha + 20))

            # Icons for negative types
            if self.pu_type == REVERSE_CONTROLS:
                # Two arrows pointing LEFT (mirrored draw_arrows)
                size = 11
                col = self.color
                for dy_off in (-size // 2, size // 2):
                    pts = [
                        (cx + size // 2, cy + dy_off - size // 4),
                        (cx,             cy + dy_off),
                        (cx + size // 2, cy + dy_off + size // 4),
                    ]
                    pygame.draw.polygon(screen, col, pts)
                    pygame.draw.line(screen, col,
                                     (cx + size, cy + dy_off),
                                     (cx + size // 2, cy + dy_off), 2)

            elif self.pu_type == SPEED_DOWN:
                # Downward lightning bolt (same shape but pointing down)
                col = self.color
                size = 13
                pts = [
                    (cx,              cy + size),
                    (cx + size // 3,  cy),
                    (cx,              cy + size // 6),
                    (cx + size // 3,  cy - size),
                    (cx - size // 3,  cy),
                    (cx,              cy - size // 6),
                ]
                pygame.draw.polygon(screen, col, pts)

            elif self.pu_type == SHOT_REDUCE:
                # Single dot in centre
                pygame.draw.circle(screen, self.color, (cx, cy), 5)

            elif self.pu_type == WEAPON_CURSE:
                # Broken star: draw star then X over it in dark red
                draw_star_shape(screen, (100, 0, 140), (cx, cy),
                                r - 4, (r - 4) // 2, 5, angle_rad)
                # X overlay
                x_col = (160, 0, 0)
                x_size = r - 6
                pygame.draw.line(screen, x_col,
                                 (cx - x_size, cy - x_size),
                                 (cx + x_size, cy + x_size), 2)
                pygame.draw.line(screen, x_col,
                                 (cx + x_size, cy - x_size),
                                 (cx - x_size, cy + x_size), 2)

        else:
            # Positive power-up — original drawing
            draw_circle_alpha(screen, self.color, (cx, cy), r + 8, 55)
            draw_circle_alpha(screen, self.color, (cx, cy), r + 4, 80)

            pygame.draw.circle(screen, (20, 20, 40), (cx, cy), r)
            pygame.draw.circle(screen, self.color, (cx, cy), r, 2)

            if self.pu_type == SPEED_UP:
                draw_lightning_bolt(screen, self.color, cx, cy, 13)

            elif self.pu_type == MULTISHOT:
                draw_arrows(screen, self.color, cx, cy, 11)

            elif self.pu_type == WEAPON_UPGRADE:
                draw_star_shape(screen, self.color, (cx, cy),
                                r - 4, (r - 4) // 2, 5, angle_rad)

            elif self.pu_type == SHADOW_CLONE:
                draw_humanoid(screen, self.color, cx, cy, 11, 200)

            elif self.pu_type == HEALTH_UP:
                draw_cross(screen, self.color, cx, cy, 9, 4)

            elif self.pu_type == BOMB:
                # Bomb icon: dark sphere + fuse
                pygame.draw.circle(screen, (30, 30, 30), (cx, cy + 2), 10)
                pygame.draw.circle(screen, (255, 120, 0), (cx, cy + 2), 10, 2)
                # Fuse line
                fuse_pts = [(cx, cy - 8), (cx + 4, cy - 12), (cx + 2, cy - 16)]
                pygame.draw.lines(screen, (180, 140, 40), False, fuse_pts, 2)
                # Spark at fuse tip
                spark_a = int(abs(math.sin(self.bob_phase * 3)) * 180 + 75)
                draw_circle_alpha(screen, (255, 200, 50), (cx + 2, cy - 16), 4, spark_a)


class PowerUpManager:
    def __init__(self) -> None:
        self.powerups: list[PowerUp] = []

    def spawn(self, pos: tuple, pu_type: str | None = None, level: int = 1) -> None:
        """Spawn a power-up at pos. If pu_type is None, pick randomly with level gating."""
        if pu_type is None:
            # 40% chance negative, 60% positive
            if random.random() < 0.40:
                chosen_type = random.choice(NEGATIVE_TYPES)
            else:
                # Build allowed positive pool based on level
                pool = list(POSITIVE_TYPES)
                if level < 3:
                    pool = [t for t in pool if t != WEAPON_UPGRADE]
                if level < 2:
                    pool = [t for t in pool if t not in (SHADOW_CLONE, BOMB)]
                if not pool:
                    pool = [SPEED_UP, MULTISHOT, HEALTH_UP]
                chosen_type = random.choice(pool)
        else:
            chosen_type = pu_type

        negative = chosen_type in NEGATIVE_TYPES
        self.powerups.append(PowerUp(pos[0], pos[1], chosen_type, negative=negative))

    def update(self, player) -> list[str]:
        """Update all power-ups; return list of collected type strings."""
        collected: list[str] = []
        for pu in self.powerups:
            pu.update()
            if not pu.dead and pu.check_collect(player):
                collected.append(pu.pu_type)
        self.powerups = [p for p in self.powerups if not p.dead]
        return collected

    def draw(self, screen: pygame.Surface) -> None:
        for pu in self.powerups:
            pu.draw(screen)
