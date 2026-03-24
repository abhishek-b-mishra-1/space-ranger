# assets.py — Color constants and drawing helpers

import pygame
import math

# ── Colors ────────────────────────────────────────────────────────────────────
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
GREY        = (160, 160, 160)
DARK_GREY   = (80,  80,  80)
RED         = (220, 40,  40)
ORANGE      = (255, 140, 0)
YELLOW      = (255, 220, 0)
GREEN       = (50,  220, 50)
CYAN        = (0,   230, 255)
BLUE        = (30,  80,  220)
PURPLE      = (160, 0,   220)
PINK        = (255, 80,  180)
DARK_BLUE   = (5,   5,   30)
BROWN       = (100, 60,  20)
DARK_BROWN  = (60,  35,  10)

# ── Drawing helpers ────────────────────────────────────────────────────────────

def draw_circle_alpha(surface: pygame.Surface, color: tuple, center: tuple,
                      radius: int, alpha: int = 128) -> None:
    """Draw a filled circle with per-call alpha onto *surface*."""
    tmp = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    r, g, b = color[:3]
    pygame.draw.circle(tmp, (r, g, b, alpha), (radius, radius), radius)
    surface.blit(tmp, (center[0] - radius, center[1] - radius))


def draw_star_shape(surface: pygame.Surface, color: tuple, center: tuple,
                    outer_r: int, inner_r: int, points: int = 5,
                    angle_offset: float = 0.0) -> None:
    """Draw a star polygon."""
    pts = []
    for i in range(points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        a = math.pi / points * i + angle_offset - math.pi / 2
        pts.append((center[0] + r * math.cos(a),
                    center[1] + r * math.sin(a)))
    pygame.draw.polygon(surface, color, pts)


def draw_lightning_bolt(surface: pygame.Surface, color: tuple,
                        cx: int, cy: int, size: int = 14) -> None:
    """Draw a simple lightning-bolt shape."""
    pts = [
        (cx,          cy - size),
        (cx - size // 3, cy),
        (cx,          cy - size // 6),
        (cx - size // 3, cy + size),
        (cx + size // 3, cy),
        (cx,          cy + size // 6),
    ]
    pygame.draw.polygon(surface, color, pts)


def draw_arrows(surface: pygame.Surface, color: tuple,
                cx: int, cy: int, size: int = 12) -> None:
    """Draw three small right-pointing arrows for multishot icon."""
    for dy in (-size // 2, 0, size // 2):
        pts = [
            (cx - size // 2, cy + dy - size // 4),
            (cx,             cy + dy),
            (cx - size // 2, cy + dy + size // 4),
        ]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.line(surface, color,
                         (cx - size, cy + dy),
                         (cx - size // 2, cy + dy), 2)


def draw_cross(surface: pygame.Surface, color: tuple,
               cx: int, cy: int, size: int = 10, thickness: int = 4) -> None:
    """Draw a plus/cross shape."""
    pygame.draw.rect(surface, color,
                     (cx - thickness // 2, cy - size, thickness, size * 2))
    pygame.draw.rect(surface, color,
                     (cx - size, cy - thickness // 2, size * 2, thickness))


def draw_humanoid(surface: pygame.Surface, color: tuple,
                  cx: int, cy: int, size: int = 12, alpha: int = 255) -> None:
    """Draw a tiny humanoid silhouette (for shadow clone icon)."""
    tmp = pygame.Surface((size * 2 + 4, size * 3 + 4), pygame.SRCALPHA)
    r, g, b = color[:3]
    c = (r, g, b, alpha)
    ox, oy = size + 2, size // 2 + 2
    # head
    pygame.draw.circle(tmp, c, (ox, oy), size // 3)
    # body
    pygame.draw.rect(tmp, c, (ox - size // 5, oy + size // 3,
                               size * 2 // 5, size * 2 // 3))
    # legs
    pygame.draw.line(tmp, c,
                     (ox - size // 6, oy + size),
                     (ox - size // 3, oy + size * 3 // 2), 2)
    pygame.draw.line(tmp, c,
                     (ox + size // 6, oy + size),
                     (ox + size // 3, oy + size * 3 // 2), 2)
    surface.blit(tmp, (cx - size - 2, cy - size // 2 - 2))
