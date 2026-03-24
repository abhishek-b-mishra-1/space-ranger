# effects.py — Visual particle effects: explosions and hit sparks

import pygame
import math
import random

# ── Explosion Particle ────────────────────────────────────────────────────────

class ExplosionParticle:
    def __init__(self, x: float, y: float, color: tuple,
                 speed: float, angle: float, size: float, lifetime: int) -> None:
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.size = size
        self.initial_size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94
        self.lifetime -= 1
        # Shrink as lifetime decreases
        progress = self.lifetime / self.max_lifetime
        self.size = self.initial_size * progress

    @property
    def dead(self) -> bool:
        return self.lifetime <= 0

    def draw(self, screen: pygame.Surface) -> None:
        if self.dead or self.size < 0.5:
            return
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        r_int = max(1, int(self.size))
        surf_size = r_int * 2 + 2
        tmp = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        r, g, b = self.color[:3]
        pygame.draw.circle(tmp, (r, g, b, alpha),
                           (r_int + 1, r_int + 1), r_int)
        screen.blit(tmp, (int(self.x) - r_int - 1, int(self.y) - r_int - 1))


# ── Explosion ─────────────────────────────────────────────────────────────────

_EXPLOSION_CONFIGS = {
    "small": {
        "count": 15,
        "colors": [(255, 140, 0), (255, 200, 0), (255, 80, 0)],
        "speed_range": (1.5, 4.0),
        "size_range": (2.0, 5.0),
        "lifetime_range": (18, 30),  # frames, ~0.5s at 60fps
        "ring_max_r": 35,
        "ring_duration": 20,
    },
    "medium": {
        "count": 25,
        "colors": [(255, 140, 0), (255, 60, 0), (255, 255, 200), (200, 80, 0)],
        "speed_range": (2.0, 6.0),
        "size_range": (2.5, 7.0),
        "lifetime_range": (25, 42),  # ~0.7s
        "ring_max_r": 55,
        "ring_duration": 28,
    },
    "large": {
        "count": 50,
        "colors": [
            (255, 140, 0), (255, 60, 0), (255, 255, 100),
            (200, 200, 255), (255, 180, 80), (255, 255, 255),
        ],
        "speed_range": (2.5, 9.0),
        "size_range": (3.0, 9.0),
        "lifetime_range": (40, 72),  # ~1.2s
        "ring_max_r": 90,
        "ring_duration": 45,
    },
    "boss": {
        "count": 100,
        "colors": [
            (255, 140, 0), (255, 60, 0), (255, 255, 100),
            (200, 200, 255), (255, 180, 80), (255, 255, 255),
            (255, 80, 200), (100, 200, 255),
        ],
        "speed_range": (3.0, 14.0),
        "size_range": (3.5, 12.0),
        "lifetime_range": (70, 120),  # ~2s
        "ring_max_r": 140,
        "ring_duration": 80,
    },
}


class Explosion:
    def __init__(self, x: float, y: float, size: str = "small") -> None:
        self.x = x
        self.y = y
        self.size = size
        cfg = _EXPLOSION_CONFIGS.get(size, _EXPLOSION_CONFIGS["small"])

        self.particles: list[ExplosionParticle] = []
        colors = cfg["colors"]
        sp_lo, sp_hi = cfg["speed_range"]
        sz_lo, sz_hi = cfg["size_range"]
        lt_lo, lt_hi = cfg["lifetime_range"]

        for _ in range(cfg["count"]):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(sp_lo, sp_hi)
            color = random.choice(colors)
            sz    = random.uniform(sz_lo, sz_hi)
            lt    = random.randint(lt_lo, lt_hi)
            self.particles.append(
                ExplosionParticle(x, y, color, speed, angle, sz, lt)
            )

        # Flash ring
        self.ring_radius = 2.0
        self.ring_max_r  = float(cfg["ring_max_r"])
        self.ring_alpha  = 255
        self.ring_duration = cfg["ring_duration"]
        self._ring_timer = 0

    def update(self) -> None:
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.dead]

        # Expand ring
        if self._ring_timer < self.ring_duration:
            self._ring_timer += 1
            progress = self._ring_timer / self.ring_duration
            self.ring_radius = self.ring_max_r * progress
            self.ring_alpha  = int(255 * (1.0 - progress))

    @property
    def dead(self) -> bool:
        return len(self.particles) == 0 and self._ring_timer >= self.ring_duration

    def draw(self, screen: pygame.Surface) -> None:
        # Draw ring
        if self._ring_timer < self.ring_duration and self.ring_alpha > 0:
            r_int = max(1, int(self.ring_radius))
            surf_size = (r_int + 2) * 2
            tmp = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            pygame.draw.circle(
                tmp, (255, 220, 100, self.ring_alpha),
                (r_int + 1, r_int + 1), r_int, max(2, r_int // 6)
            )
            screen.blit(tmp, (int(self.x) - r_int - 1, int(self.y) - r_int - 1))

        # Draw particles
        for p in self.particles:
            p.draw(screen)


# ── Hit Spark ─────────────────────────────────────────────────────────────────

class HitSpark:
    COUNT    = 5
    LIFETIME = 12   # frames (~0.2s)

    def __init__(self, x: float, y: float) -> None:
        self.particles: list[ExplosionParticle] = []
        colors = [(255, 255, 255), (255, 240, 100), (255, 200, 50)]
        for _ in range(self.COUNT):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 4.0)
            color = random.choice(colors)
            sz    = random.uniform(1.5, 3.0)
            lt    = random.randint(8, self.LIFETIME)
            self.particles.append(
                ExplosionParticle(x, y, color, speed, angle, sz, lt)
            )

    def update(self) -> None:
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.dead]

    @property
    def dead(self) -> bool:
        return len(self.particles) == 0

    def draw(self, screen: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(screen)


# ── Effects Manager ────────────────────────────────────────────────────────────

class EffectsManager:
    def __init__(self) -> None:
        self.explosions: list[Explosion] = []
        self.sparks:     list[HitSpark]  = []

    def spawn_explosion(self, x: float, y: float, size: str = "small") -> None:
        self.explosions.append(Explosion(x, y, size))

    def spawn_spark(self, x: float, y: float) -> None:
        self.sparks.append(HitSpark(x, y))

    def update(self) -> None:
        for exp in self.explosions:
            exp.update()
        for spark in self.sparks:
            spark.update()
        self.explosions = [e for e in self.explosions if not e.dead]
        self.sparks     = [s for s in self.sparks     if not s.dead]

    def draw(self, screen: pygame.Surface) -> None:
        for exp in self.explosions:
            exp.draw(screen)
        for spark in self.sparks:
            spark.draw(screen)
