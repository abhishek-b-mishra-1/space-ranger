#!/usr/bin/env python3
# main.py — Space Ranger entry point

import sys
import os
import random
import socket
import pygame

# ── Single-instance lock (prevents multiple windows) ──────────────────────────
_LOCK_SOCKET: socket.socket | None = None

def _acquire_instance_lock() -> bool:
    global _LOCK_SOCKET
    try:
        _LOCK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _LOCK_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        _LOCK_SOCKET.bind(('127.0.0.1', 54321))
        return True
    except OSError:
        return False

# ── Game state constants ───────────────────────────────────────────────────────
MENU      = "MENU"
PLAYING   = "PLAYING"
GAME_OVER = "GAME_OVER"
PAUSED    = "PAUSED"

SCREEN_W = 800
SCREEN_H = 600
FPS      = 60

# ── Level system ──────────────────────────────────────────────────────────────
LEVEL_THRESHOLDS = [0, 3000, 7500, 14000, 23000, 36000, 54000, 78000, 110000, 150000]
# index 0 → level 1, index 1 → level 2, …, index 9 → level 10

WORLD_NAMES = {
    1:  'DEEP SPACE',
    2:  'NEBULA FIELDS',
    3:  'ASTEROID HIVE',
    4:  'ALIEN TERRITORY',
    5:  'ICE SECTOR',
    6:  'VOLCANIC VOID',
    7:  'THE ABYSS',
    8:  'DARK NEBULA',
    9:  'VOID STORM',
    10: 'FINAL FRONTIER',
}

# ── Imports ────────────────────────────────────────────────────────────────────
from background import Background
from player     import Player
from enemies    import EnemyManager
from powerups   import (PowerUpManager,
                         SPEED_UP, MULTISHOT, WEAPON_UPGRADE,
                         SHADOW_CLONE, HEALTH_UP, BOMB,
                         REVERSE_CONTROLS, SPEED_DOWN, SHOT_REDUCE, WEAPON_CURSE)
from weapons    import WeaponSystem, LASER, FIRE, MAGNETIC
from game_ui    import (draw_hud, draw_menu, draw_game_over, draw_pause,
                        draw_level_transition)
from sounds     import SoundManager
from effects    import EffectsManager
from boss       import BossManager
from enemies    import AlienHead   # for minion spawns

_NEGATIVE_PU_TYPES = (REVERSE_CONTROLS, SPEED_DOWN, SHOT_REDUCE, WEAPON_CURSE)


def _score_to_level(score: int) -> int:
    """Return level (1–10) for the given score."""
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if score >= threshold:
            level = i + 1
    return min(level, 10)


def _get_level_music(level: int) -> str:
    """Return music track name for the given level."""
    if level <= 2:
        return 'menu'
    elif level <= 6:
        return 'action'
    else:
        return 'danger'


# ── Game session ──────────────────────────────────────────────────────────────
class Game:
    """Encapsulates one full play-through session."""

    def __init__(self, screen: pygame.Surface,
                 sounds: SoundManager) -> None:
        self.screen        = screen
        self.sounds        = sounds
        self.background    = Background(SCREEN_W, SCREEN_H, level=1)
        self.player        = Player()
        self.enemy_manager = EnemyManager()
        self.powerup_mgr   = PowerUpManager()
        self.effects       = EffectsManager()
        self.boss_manager  = BossManager()
        self.projectiles: list = []
        self.score = 0
        self._prev_hp = self.player.hp

        # Level system
        self.current_level = 1
        self.level_transition_timer = 180   # show level 1 banner at game start
        self._boss_music_active = False

        # Timed effects (effect_name -> frames_remaining)
        self._timed_effects: dict = {}

        # Bomb state
        self._bomb_flash_timer = 0   # screen-white flash frames remaining
        self._bomb_cooldown = 0      # prevent double-detonation

        # Start menu music (level 1)
        self.sounds.play_music('menu')

    # ── Level management ──────────────────────────────────────────────────────
    def _check_level(self) -> None:
        """Compare score to thresholds, trigger level-up if needed."""
        new_level = _score_to_level(self.score)
        if new_level != self.current_level:
            self.current_level = new_level
            # Background only has 7 themes — cap at 7
            self.background.set_level(min(new_level, 7))
            self.enemy_manager.set_level(new_level)
            # Suppress banner and music change during boss encounters
            boss_busy = (self._boss_music_active or
                         self.boss_manager.warning_active or
                         self.boss_manager.boss_active)
            if not boss_busy:
                self.level_transition_timer = 180
                self.sounds.play_music(_get_level_music(new_level))

    # ── Apply a collected power-up ────────────────────────────────────────────
    def _apply_powerup(self, pu_type: str) -> None:
        p = self.player

        # ── Positive types ────────────────────────────────────────────────────
        if pu_type == SPEED_UP:
            p.upgrade_speed()
            self.sounds.play("powerup")

        elif pu_type == MULTISHOT:
            p.upgrade_multishot()
            self.sounds.play("powerup")

        elif pu_type == WEAPON_UPGRADE:
            p.upgrade_weapon()
            # Weapon gating: if level < 3, revert to LASER
            if self.current_level < 3:
                p.weapon_system.shot_type = LASER
            self.sounds.play("powerup")

        elif pu_type == SHADOW_CLONE:
            p.add_shadow()
            self.sounds.play("powerup")

        elif pu_type == HEALTH_UP:
            p.heal(2)
            self.sounds.play("powerup")

        elif pu_type == BOMB:
            p.add_bomb()
            self.sounds.play("powerup")

        # ── Negative types ────────────────────────────────────────────────────
        elif pu_type == REVERSE_CONTROLS:
            self._timed_effects['REVERSE'] = 480   # 8 seconds at 60 fps
            self.player.reversed_controls = True
            self.sounds.play("player_hit")

        elif pu_type == SPEED_DOWN:
            p.weapon_system.bullet_speed_multiplier = max(
                0.5, p.weapon_system.bullet_speed_multiplier * 0.55)
            self.sounds.play("player_hit")

        elif pu_type == SHOT_REDUCE:
            p.weapon_system.multishot_count = max(
                1, p.weapon_system.multishot_count - 1)
            self.sounds.play("player_hit")

        elif pu_type == WEAPON_CURSE:
            p.weapon_system.shot_type = LASER
            p.weapon_system.multishot_count = 1
            self.sounds.play("player_hit")

    # ── Bomb detonation ───────────────────────────────────────────────────────
    def _detonate_bomb(self) -> None:
        if self.player.bombs <= 0:
            return
        self.player.bombs -= 1
        self._bomb_flash_timer = 12   # 12-frame white flash
        self._bomb_cooldown = 30

        # Kill all enemies and collect explosion positions
        for (ex, ey, esize) in self.enemy_manager.kill_all_enemies():
            self.effects.spawn_explosion(ex, ey, esize)
            self.score += 5   # small bonus per enemy cleared

        # Extra large explosion bursts scattered across screen
        for _ in range(8):
            rx = random.randint(100, 700)
            ry = random.randint(60, 540)
            self.effects.spawn_explosion(rx, ry, "large")

        # Deal heavy damage to boss
        if self.boss_manager.boss_active and self.boss_manager.current_boss:
            self.boss_manager.current_boss.take_damage(80)

        self.sounds.play("explosion_large")

    # ── One frame of gameplay ─────────────────────────────────────────────────
    def update(self) -> None:
        keys  = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()

        # Bomb detonation
        if self._bomb_cooldown > 0:
            self._bomb_cooldown -= 1
        if self._bomb_flash_timer > 0:
            self._bomb_flash_timer -= 1

        # Apply reversed controls flag before player.update reads keys
        self.player.reversed_controls = 'REVERSE' in self._timed_effects

        # Player movement
        self.player.update(keys)

        # ── Expire timed effects each frame ───────────────────────────────────
        for k in list(self._timed_effects):
            self._timed_effects[k] -= 1
            if self._timed_effects[k] <= 0:
                del self._timed_effects[k]
                if k == 'REVERSE':
                    self.player.reversed_controls = False

        # ── Shooting ──────────────────────────────────────────────────────────
        new_shots = self.player.handle_shoot(keys, mouse)
        if new_shots:
            wtype = self.player.weapon_system.shot_type
            if wtype == LASER:
                self.sounds.play("laser")
            elif wtype == FIRE:
                self.sounds.play("fire_shot")
            elif wtype == MAGNETIC:
                self.sounds.play("magnetic_shot")
        self.projectiles += new_shots

        # Weapons update
        self.player.weapon_system.update_projectiles(
            self.projectiles,
            self.enemy_manager.get_all_sequences()
        )

        # ── Enemy manager pause flag ──────────────────────────────────────────
        self.enemy_manager.paused = self.boss_manager.boss_active

        # ── Enemies update ────────────────────────────────────────────────────
        self.enemy_manager.update()

        # ── Score from killing enemies ────────────────────────────────────────
        self.score += self.enemy_manager.check_player_shots(self.projectiles)

        # ── Explosion events from enemy deaths ────────────────────────────────
        for (ex, ey, esize) in self.enemy_manager.pop_explosion_events():
            self.effects.spawn_explosion(ex, ey, esize)
            if esize == "small":
                self.sounds.play("explosion_small")
            else:
                self.sounds.play("explosion_medium")

        # ── Hit sparks ────────────────────────────────────────────────────────
        for (sx, sy) in self.enemy_manager.pop_hit_sparks():
            self.effects.spawn_spark(sx, sy)

        # ── Sequence completion power-up drops — 25% chance only ──────────────
        for drop_pos in self.enemy_manager.pop_powerup_drops():
            self.score += 100
            if random.random() < 0.25:
                self.powerup_mgr.spawn(drop_pos, level=self.current_level)

        # ── Power-ups collected ───────────────────────────────────────────────
        collected = self.powerup_mgr.update(self.player)
        for pu_type in collected:
            self._apply_powerup(pu_type)

        # ── Player hit by enemy body ──────────────────────────────────────────
        if not self.player.invincible:
            if self.enemy_manager.check_player_collision(self.player.get_rect()):
                self.player.take_damage()
                self.sounds.play("player_hit")

        # ── Player hit by enemy shot ──────────────────────────────────────────
        if not self.player.invincible:
            if self.enemy_manager.check_player_shot_hits(self.player.get_rect()):
                self.player.take_damage()
                self.sounds.play("player_hit")

        # ── Shadow clone takes hits ───────────────────────────────────────────
        if self.player.shadow_clone and not self.player.shadow_clone.dead:
            hits = self.enemy_manager.check_shadow_collision(
                self.player.shadow_clone.get_rect())
            for _ in range(hits):
                self.player.shadow_clone.take_hit()

        # ── Boss system ───────────────────────────────────────────────────────
        boss_was_active = self.boss_manager.boss_active
        self.boss_manager.update(self.player.get_rect())   # process deaths FIRST
        boss_now_active = self.boss_manager.boss_active    # check AFTER update
        # check_spawn AFTER update so defeated_scores is already populated
        self.boss_manager.check_spawn(self.score)

        # Boss just became active → switch to boss music
        if not boss_was_active and boss_now_active:
            self.sounds.play_music('boss')
            self._boss_music_active = True

        # Boss shots vs player
        if not self.player.invincible:
            if self.boss_manager.check_player_shot_hits(self.player.get_rect()):
                self.player.take_damage()
                self.sounds.play("player_hit")

        # Score from boss kills
        boss_score = self.boss_manager.check_player_shots(self.projectiles)
        self.score += boss_score

        # Score events (boss death bonus)
        for bonus in self.boss_manager.pop_score_events():
            self.score += bonus

        # Boss death explosions — also revert music
        boss_death_events = self.boss_manager.pop_boss_death_events()
        for (bx, by) in boss_death_events:
            self.effects.spawn_explosion(bx, by, "boss")
            self.sounds.play("explosion_large")

        # If boss just died: advance to next level immediately + revert music
        if boss_death_events and self._boss_music_active:
            self._boss_music_active = False
            # Jump score to next level threshold so level-up triggers this frame
            next_level = self.current_level + 1
            if next_level <= 10:
                next_threshold = LEVEL_THRESHOLDS[next_level - 1]
                if self.score < next_threshold:
                    self.score = next_threshold
            self.sounds.play_music(_get_level_music(self.current_level))

        # Minion spawns from bosses with pop_minions
        for (mx, my) in self.boss_manager.pop_minions():
            from enemies import EnemySequence
            from enemies import AlienHead as AH
            alien = AH(mx, my,
                       shoot_interval=self.enemy_manager._alien_shoot_interval)
            seq = EnemySequence.__new__(EnemySequence)
            seq.seq_type = "ALIEN_PATROL"
            seq.speed_mult = self.enemy_manager._speed_mult
            seq.hp_mult = self.enemy_manager._hp_mult
            seq.alien_shoot_interval = self.enemy_manager._alien_shoot_interval
            seq.drone_shoot_interval = self.enemy_manager._drone_shoot_interval
            seq.enemies = [alien]
            seq.completed = False
            seq.reward_pos = None
            seq.explosion_events = []
            seq.hit_sparks = []
            self.enemy_manager.sequences.append(seq)

        # ── Level check ───────────────────────────────────────────────────────
        self._check_level()

        # ── Level transition timer ────────────────────────────────────────────
        if self.level_transition_timer > 0:
            self.level_transition_timer -= 1

        # ── Background ────────────────────────────────────────────────────────
        self.background.update()

        # ── Effects update ────────────────────────────────────────────────────
        self.effects.update()

    def draw(self) -> None:
        self.background.draw(self.screen)
        self.powerup_mgr.draw(self.screen)
        self.enemy_manager.draw(self.screen)
        self.player.weapon_system.draw_projectiles(self.screen, self.projectiles)
        self.player.draw(self.screen)

        self.effects.draw(self.screen)
        self.boss_manager.draw(self.screen)

        # HUD
        draw_hud(self.screen, self.player,
                 self.player.weapon_system, self.score,
                 level=self.current_level, bombs=self.player.bombs)

        # Bomb flash overlay
        if self._bomb_flash_timer > 0:
            flash_alpha = int(220 * self._bomb_flash_timer / 12)
            flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash.fill((255, 200, 80, flash_alpha))
            self.screen.blit(flash, (0, 0))

        # Boss health bar
        self.boss_manager.draw_health_bar(self.screen)

        # Level transition overlay
        if self.level_transition_timer > 0:
            draw_level_transition(
                self.screen,
                self.current_level,
                WORLD_NAMES.get(self.current_level, ''),
                self.level_transition_timer,
            )

        # Reversed controls indicator
        if 'REVERSE' in self._timed_effects:
            font = pygame.font.SysFont("consolas", 22, bold=True)
            t = font.render("!! CONTROLS REVERSED !!", True, (220, 40, 40))
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H - 40))

    @property
    def player_dead(self) -> bool:
        return self.player.is_dead


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    if not _acquire_instance_lock():
        print("Space Ranger is already running.")
        return

    pygame.init()
    pygame.display.set_caption("Space Ranger")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock  = pygame.time.Clock()

    sounds = SoundManager()

    state: str = MENU
    game: Game | None = None

    # Menu background + music
    menu_bg = Background(SCREEN_W, SCREEN_H, level=1)
    sounds.play_music('menu')

    while True:
        clock.tick(FPS)

        # ── Events ─────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # ── MENU ───────────────────────────────────────────────────────
                if state == MENU:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                     pygame.K_SPACE):
                        sounds.stop_music()
                        game  = Game(screen, sounds)
                        state = PLAYING

                # ── PLAYING ────────────────────────────────────────────────────
                elif state == PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        state = PAUSED
                    elif event.key == pygame.K_b and game is not None:
                        if game._bomb_cooldown <= 0:
                            game._detonate_bomb()

                # ── PAUSED ─────────────────────────────────────────────────────
                elif state == PAUSED:
                    if event.key == pygame.K_ESCAPE:
                        state = PLAYING

                # ── GAME OVER ──────────────────────────────────────────────────
                elif state == GAME_OVER:
                    if event.key == pygame.K_r:
                        sounds.stop_music()
                        game  = Game(screen, sounds)
                        state = PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        sounds.stop_music()
                        state = MENU
                        game  = None
                        sounds.play_music('menu')

        # ── State logic ────────────────────────────────────────────────────────
        if state == MENU:
            menu_bg.update()
            menu_bg.draw(screen)
            draw_menu(screen)

        elif state == PLAYING and game is not None:
            game.update()
            game.draw()
            if game.player_dead:
                sounds.stop_music()
                state = GAME_OVER

        elif state == PAUSED and game is not None:
            game.draw()
            draw_pause(screen)

        elif state == GAME_OVER and game is not None:
            game.background.update()
            game.background.draw(screen)
            draw_game_over(screen, game.score)

        pygame.display.flip()


if __name__ == "__main__":
    main()
