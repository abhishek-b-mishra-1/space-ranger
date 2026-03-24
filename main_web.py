#!/usr/bin/env python3
# main_web.py — Web entry point for Pygbag (async game loop, no socket lock)

import sys
import os
import random
import asyncio
import pygame

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
class SoundManager:
    """Silent stub for web — browser blocks audio autoplay before user interaction."""
    def play(self, name: str) -> None: pass
    def play_music(self, track: str) -> None: pass
    def stop_music(self) -> None: pass
    def cleanup(self) -> None: pass
from effects    import EffectsManager
from boss       import BossManager
from enemies    import AlienHead

_NEGATIVE_PU_TYPES = (REVERSE_CONTROLS, SPEED_DOWN, SHOT_REDUCE, WEAPON_CURSE)


def _score_to_level(score: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if score >= threshold:
            level = i + 1
    return min(level, 10)


def _get_level_music(level: int) -> str:
    if level <= 2:
        return 'menu'
    elif level <= 6:
        return 'action'
    else:
        return 'danger'


# ── Game class (identical to main.py) ─────────────────────────────────────────
class Game:
    def __init__(self, screen: pygame.Surface, sounds: SoundManager) -> None:
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
        self.current_level = 1
        self.level_transition_timer = 180
        self._boss_music_active = False
        self._timed_effects: dict = {}
        self._bomb_flash_timer = 0
        self._bomb_cooldown = 0
        self.sounds.play_music('menu')

    def _check_level(self) -> None:
        new_level = _score_to_level(self.score)
        if new_level != self.current_level:
            self.current_level = new_level
            self.background.set_level(min(new_level, 7))
            self.enemy_manager.set_level(new_level)
            boss_busy = (self._boss_music_active or
                         self.boss_manager.warning_active or
                         self.boss_manager.boss_active)
            if not boss_busy:
                self.level_transition_timer = 180
                self.sounds.play_music(_get_level_music(new_level))

    def _apply_powerup(self, pu_type: str) -> None:
        p = self.player
        if pu_type == SPEED_UP:
            p.upgrade_speed()
            self.sounds.play("powerup")
        elif pu_type == MULTISHOT:
            p.upgrade_multishot()
            self.sounds.play("powerup")
        elif pu_type == WEAPON_UPGRADE:
            p.upgrade_weapon()
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
        elif pu_type == REVERSE_CONTROLS:
            self._timed_effects['REVERSE'] = 480
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

    def _detonate_bomb(self) -> None:
        if self.player.bombs <= 0:
            return
        self.player.bombs -= 1
        self._bomb_flash_timer = 12
        self._bomb_cooldown = 30
        for (ex, ey, esize) in self.enemy_manager.kill_all_enemies():
            self.effects.spawn_explosion(ex, ey, esize)
            self.score += 5
        for _ in range(8):
            rx = random.randint(100, 700)
            ry = random.randint(60, 540)
            self.effects.spawn_explosion(rx, ry, "large")
        if self.boss_manager.boss_active and self.boss_manager.current_boss:
            self.boss_manager.current_boss.take_damage(80)
        self.sounds.play("explosion_large")

    def update(self) -> None:
        keys  = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        if self._bomb_cooldown > 0:
            self._bomb_cooldown -= 1
        if self._bomb_flash_timer > 0:
            self._bomb_flash_timer -= 1
        self.player.reversed_controls = 'REVERSE' in self._timed_effects
        self.player.update(keys)
        for k in list(self._timed_effects):
            self._timed_effects[k] -= 1
            if self._timed_effects[k] <= 0:
                del self._timed_effects[k]
                if k == 'REVERSE':
                    self.player.reversed_controls = False
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
        self.player.weapon_system.update_projectiles(
            self.projectiles,
            self.enemy_manager.get_all_sequences()
        )
        self.enemy_manager.paused = self.boss_manager.boss_active
        self.enemy_manager.update()
        self.score += self.enemy_manager.check_player_shots(self.projectiles)
        for (ex, ey, esize) in self.enemy_manager.pop_explosion_events():
            self.effects.spawn_explosion(ex, ey, esize)
            if esize == "small":
                self.sounds.play("explosion_small")
            else:
                self.sounds.play("explosion_medium")
        for (sx, sy) in self.enemy_manager.pop_hit_sparks():
            self.effects.spawn_spark(sx, sy)
        for drop_pos in self.enemy_manager.pop_powerup_drops():
            self.score += 100
            if random.random() < 0.25:
                self.powerup_mgr.spawn(drop_pos, level=self.current_level)
        collected = self.powerup_mgr.update(self.player)
        for pu_type in collected:
            self._apply_powerup(pu_type)
        if not self.player.invincible:
            if self.enemy_manager.check_player_collision(self.player.get_rect()):
                self.player.take_damage()
                self.sounds.play("player_hit")
        if not self.player.invincible:
            if self.enemy_manager.check_player_shot_hits(self.player.get_rect()):
                self.player.take_damage()
                self.sounds.play("player_hit")
        if self.player.shadow_clone and not self.player.shadow_clone.dead:
            hits = self.enemy_manager.check_shadow_collision(
                self.player.shadow_clone.get_rect())
            for _ in range(hits):
                self.player.shadow_clone.take_hit()
        boss_was_active = self.boss_manager.boss_active
        self.boss_manager.update(self.player.get_rect())
        boss_now_active = self.boss_manager.boss_active
        self.boss_manager.check_spawn(self.score)
        if not boss_was_active and boss_now_active:
            self.sounds.play_music('boss')
            self._boss_music_active = True
        if not self.player.invincible:
            if self.boss_manager.check_player_shot_hits(self.player.get_rect()):
                self.player.take_damage()
                self.sounds.play("player_hit")
        boss_score = self.boss_manager.check_player_shots(self.projectiles)
        self.score += boss_score
        for bonus in self.boss_manager.pop_score_events():
            self.score += bonus
        boss_death_events = self.boss_manager.pop_boss_death_events()
        for (bx, by) in boss_death_events:
            self.effects.spawn_explosion(bx, by, "boss")
            self.sounds.play("explosion_large")
        if boss_death_events and self._boss_music_active:
            self._boss_music_active = False
            next_level = self.current_level + 1
            if next_level <= 10:
                next_threshold = LEVEL_THRESHOLDS[next_level - 1]
                if self.score < next_threshold:
                    self.score = next_threshold
            self.sounds.play_music(_get_level_music(self.current_level))
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
        self._check_level()
        if self.level_transition_timer > 0:
            self.level_transition_timer -= 1
        self.background.update()
        self.effects.update()

    def draw(self) -> None:
        self.background.draw(self.screen)
        self.powerup_mgr.draw(self.screen)
        self.enemy_manager.draw(self.screen)
        self.player.weapon_system.draw_projectiles(self.screen, self.projectiles)
        self.player.draw(self.screen)
        self.effects.draw(self.screen)
        self.boss_manager.draw(self.screen)
        draw_hud(self.screen, self.player,
                 self.player.weapon_system, self.score,
                 level=self.current_level, bombs=self.player.bombs)
        if self._bomb_flash_timer > 0:
            flash_alpha = int(220 * self._bomb_flash_timer / 12)
            flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash.fill((255, 200, 80, flash_alpha))
            self.screen.blit(flash, (0, 0))
        self.boss_manager.draw_health_bar(self.screen)
        if self.level_transition_timer > 0:
            draw_level_transition(
                self.screen,
                self.current_level,
                WORLD_NAMES.get(self.current_level, ''),
                self.level_transition_timer,
            )
        if 'REVERSE' in self._timed_effects:
            font = pygame.font.SysFont("consolas", 22, bold=True)
            t = font.render("!! CONTROLS REVERSED !!", True, (220, 40, 40))
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H - 40))

    @property
    def player_dead(self) -> bool:
        return self.player.is_dead


# ── Async main loop (required by Pygbag) ──────────────────────────────────────
async def main() -> None:
    pygame.display.init()   # only init display — skip audio to avoid browser block
    pygame.font.init()
    pygame.display.set_caption("Space Ranger")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock  = pygame.time.Clock()

    sounds = SoundManager()

    state: str = MENU
    game: Game | None = None

    menu_bg = Background(SCREEN_W, SCREEN_H, level=1)
    sounds.play_music('menu')

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return   # sys.exit() crashes in browser context

            if event.type == pygame.KEYDOWN:
                if state == MENU:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                     pygame.K_SPACE):
                        sounds.stop_music()
                        game  = Game(screen, sounds)
                        state = PLAYING

                elif state == PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        state = PAUSED
                    elif event.key == pygame.K_b and game is not None:
                        if game._bomb_cooldown <= 0:
                            game._detonate_bomb()

                elif state == PAUSED:
                    if event.key == pygame.K_ESCAPE:
                        state = PLAYING

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
        await asyncio.sleep(0)   # yield to browser event loop each frame


asyncio.run(main())
