# sounds.py — Procedural sound generation using struct + pygame.mixer

import struct
import math
import random
import io
import tempfile
import os
import pygame

SAMPLE_RATE = 22050


def _make(samples: list) -> pygame.mixer.Sound:
    """Pack a list of float samples [-1.0, 1.0] into a pygame Sound."""
    data = struct.pack(
        '<%dh' % len(samples),
        *[max(-32768, min(32767, int(s * 32767))) for s in samples]
    )
    return pygame.mixer.Sound(buffer=data)


def _silence(duration: float) -> list:
    n = int(SAMPLE_RATE * duration)
    return [0.0] * n


def _write_wav_bytes(samples, sample_rate=22050):
    """Write a list of float samples to a WAV BytesIO buffer."""
    n = len(samples)
    pcm = struct.pack('<%dh' % n, *[max(-32768, min(32767, int(s * 32767))) for s in samples])
    buf = io.BytesIO()
    data_size = len(pcm)
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + data_size))
    buf.write(b'WAVE')
    buf.write(b'fmt ')
    buf.write(struct.pack('<I', 16))
    buf.write(struct.pack('<H', 1))    # PCM
    buf.write(struct.pack('<H', 1))    # mono
    buf.write(struct.pack('<I', sample_rate))
    buf.write(struct.pack('<I', sample_rate * 2))
    buf.write(struct.pack('<H', 2))
    buf.write(struct.pack('<H', 16))
    buf.write(b'data')
    buf.write(struct.pack('<I', data_size))
    buf.write(pcm)
    buf.seek(0)
    return buf


class SoundManager:
    # Note frequency table
    _FREQ = {
        'R': 0,
        'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00,
        'A3': 220.00, 'Bb3': 233.08, 'B3': 246.94,
        'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00,
        'A4': 440.00, 'Bb4': 466.16, 'B4': 493.88,
        'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46,
        'G5': 783.99, 'A5': 880.00,
        # Extra low notes
        'A2': 110.00, 'E2': 82.41, 'D2': 73.42,
    }

    def __init__(self) -> None:
        self._ok = False
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
            pygame.mixer.init()
            self._ok = True
        except Exception:
            pass

        self._sounds: dict = {}
        if self._ok:
            try:
                self._sounds["laser"]           = self._make_laser()
                self._sounds["fire_shot"]        = self._make_fire_shot()
                self._sounds["magnetic_shot"]    = self._make_magnetic_shot()
                self._sounds["explosion_small"]  = self._make_explosion_small()
                self._sounds["explosion_medium"] = self._make_explosion_medium()
                self._sounds["explosion_large"]  = self._make_explosion_large()
                self._sounds["powerup"]          = self._make_powerup()
                self._sounds["player_hit"]       = self._make_player_hit()
                self._sounds["boss_warning"]     = self._make_boss_warning()
                self._sounds["boss_shoot"]       = self._make_boss_shoot()
            except Exception:
                self._ok = False

        self._music_files: dict = {}    # name -> temp file path on disk
        self._current_music = None
        if self._ok:
            try:
                tracks = {
                    'menu':   self._make_music_menu(),
                    'action': self._make_music_action(),
                    'danger': self._make_music_danger(),
                    'boss':   self._make_music_boss(),
                }
                for name, buf in tracks.items():
                    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                    buf.seek(0)
                    tmp.write(buf.read())
                    tmp.close()
                    self._music_files[name] = tmp.name
            except Exception:
                pass

    # ── Music helpers ─────────────────────────────────────────────────────────

    def _synth_voice(self, notes: list, bpm: float,
                     wave: str = 'square', vol: float = 0.3) -> list:
        """Synthesise a sequence of notes into float samples.

        notes: list of (note_name, duration_beats)
        Returns a list of float samples.
        """
        samples = []
        beat_len = 60.0 / bpm  # seconds per beat

        for note_name, dur_beats in notes:
            note_samples_n = int(SAMPLE_RATE * beat_len * dur_beats)
            freq = self._FREQ.get(note_name, 0)

            if freq == 0 or note_name == 'R':
                # Rest
                samples.extend([0.0] * note_samples_n)
                continue

            attack_n  = int(note_samples_n * 0.05)
            decay_n   = int(note_samples_n * 0.15)
            release_n = int(note_samples_n * 0.20)
            sustain_n = note_samples_n - attack_n - decay_n - release_n
            if sustain_n < 0:
                sustain_n = 0

            for i in range(note_samples_n):
                t = i / SAMPLE_RATE

                # Envelope
                if i < attack_n:
                    env = i / max(1, attack_n)
                elif i < attack_n + decay_n:
                    env = 1.0 - 0.3 * (i - attack_n) / max(1, decay_n)
                elif i < attack_n + decay_n + sustain_n:
                    env = 0.7
                else:
                    release_pos = i - (attack_n + decay_n + sustain_n)
                    env = 0.7 * (1.0 - release_pos / max(1, release_n))
                    env = max(0.0, env)

                # Waveform
                phase = (t * freq) % 1.0
                if wave == 'square':
                    s = 1.0 if phase < 0.5 else -1.0
                elif wave == 'triangle':
                    s = 1.0 - 4.0 * abs(phase - 0.5)
                elif wave == 'sine':
                    s = math.sin(2.0 * math.pi * freq * t)
                elif wave == 'noise':
                    s = random.uniform(-1.0, 1.0)
                else:
                    s = math.sin(2.0 * math.pi * freq * t)

                samples.append(s * env * vol)

        return samples

    def _mix_voices(self, *voice_lists) -> list:
        """Mix multiple voice sample lists (may differ in length), normalise to peak 0.8."""
        if not voice_lists:
            return []

        # Pad all voices to the same length
        max_len = max(len(v) for v in voice_lists)
        padded = []
        for v in voice_lists:
            if len(v) < max_len:
                padded.append(v + [0.0] * (max_len - len(v)))
            else:
                padded.append(v)

        # Sum
        mixed = [sum(padded[vi][i] for vi in range(len(padded)))
                 for i in range(max_len)]

        # Normalise to peak 0.8
        peak = max(abs(s) for s in mixed) if mixed else 1.0
        if peak > 0.0:
            scale = 0.8 / peak
            mixed = [s * scale for s in mixed]

        return mixed

    # ── Music track builders ──────────────────────────────────────────────────

    def _make_music_menu(self) -> io.BytesIO:
        """100 BPM, 8 bars, A minor ambient/arpeggio."""
        bpm = 100

        # Melody: Am pentatonic arpeggio, 8-bar sequence
        melody_notes = [
            ('A4', 0.5), ('C5', 0.5), ('E5', 0.5), ('A5', 0.5),
            ('G5', 0.5), ('E5', 0.5), ('C5', 0.5), ('A4', 0.5),
            ('A4', 0.5), ('E5', 0.5), ('C5', 0.5), ('G5', 0.5),
            ('E5', 0.5), ('A4', 0.5), ('C5', 1.0),
            ('E5', 0.5), ('A5', 0.5), ('G5', 0.5), ('E5', 0.5),
            ('C5', 0.5), ('A4', 0.5), ('E5', 0.5), ('C5', 0.5),
            ('A4', 1.0), ('R', 1.0),
        ]

        # Bass: A3 each beat, E3 on beats 3+4 of each bar
        bass_notes = []
        for bar in range(8):
            bass_notes += [('A3', 1.0), ('A3', 1.0), ('E3', 1.0), ('E3', 1.0)]

        # Percussion: light noise blip every 4 beats
        perc_notes = []
        total_beats = 32
        for b in range(total_beats):
            if b % 4 == 0:
                perc_notes.append(('A4', 0.1))
                perc_notes.append(('R',  0.9))
            else:
                perc_notes.append(('R',  1.0))

        v_melody = self._synth_voice(melody_notes, bpm, wave='sine', vol=0.25)
        v_bass   = self._synth_voice(bass_notes,   bpm, wave='triangle', vol=0.3)
        v_perc   = self._synth_voice(perc_notes,   bpm, wave='noise', vol=0.15)

        mixed = self._mix_voices(v_melody, v_bass, v_perc)
        return _write_wav_bytes(mixed)

    def _make_music_action(self) -> io.BytesIO:
        """140 BPM, 8 bars, driving E minor."""
        bpm = 140

        # Melody: fast E minor riff
        melody_notes = []
        riff = [('E5', 0.5), ('D5', 0.5), ('B4', 0.5), ('G4', 0.5),
                ('A4', 0.5), ('B4', 0.5), ('G4', 0.5), ('E4', 0.5)]
        for _ in range(4):
            melody_notes += riff

        # Bass: E3 B3 alternating on beats
        bass_notes = []
        for bar in range(8):
            bass_notes += [('E3', 1.0), ('B3', 1.0), ('E3', 1.0), ('B3', 1.0)]

        # Percussion: noise on beats 1 and 3
        perc_notes = []
        for bar in range(8):
            perc_notes += [
                ('A4', 0.15), ('R', 0.85),
                ('R',  1.0),
                ('A4', 0.15), ('R', 0.85),
                ('R',  1.0),
            ]

        v_melody = self._synth_voice(melody_notes, bpm, wave='square', vol=0.28)
        v_bass   = self._synth_voice(bass_notes,   bpm, wave='triangle', vol=0.35)
        v_perc   = self._synth_voice(perc_notes,   bpm, wave='noise', vol=0.2)

        mixed = self._mix_voices(v_melody, v_bass, v_perc)
        return _write_wav_bytes(mixed)

    def _make_music_danger(self) -> io.BytesIO:
        """130 BPM, 8 bars, tense/dark D minor."""
        bpm = 130

        # Melody: Dm riff, slower feel
        melody_notes = []
        riff = [('D5', 1.0), ('C5', 1.0), ('Bb4', 1.0), ('A4', 1.0),
                ('G4', 1.0), ('A4', 1.0), ('Bb4', 1.0), ('C5', 1.0)]
        for _ in range(4):
            melody_notes += riff

        # Bass: D3 A3 F3 C3 repeating whole notes
        bass_notes = []
        pattern = [('D3', 2.0), ('A3', 2.0), ('F3', 2.0), ('C3', 2.0)]
        for _ in range(4):
            bass_notes += pattern

        # Percussion: noise every 2 beats
        perc_notes = []
        for b in range(16):
            if b % 2 == 0:
                perc_notes.append(('A4', 0.2))
                perc_notes.append(('R',  1.8))
            else:
                perc_notes.append(('R',  2.0))

        v_melody = self._synth_voice(melody_notes, bpm, wave='square', vol=0.25)
        v_bass   = self._synth_voice(bass_notes,   bpm, wave='triangle', vol=0.38)
        v_perc   = self._synth_voice(perc_notes,   bpm, wave='noise', vol=0.18)

        mixed = self._mix_voices(v_melody, v_bass, v_perc)
        return _write_wav_bytes(mixed)

    def _make_music_boss(self) -> io.BytesIO:
        """160 BPM, 8 bars, very intense minor second riff."""
        bpm = 160

        # Melody: aggressive rapid minor second riff
        melody_notes = []
        riff = [
            ('E5', 0.25), ('F5', 0.25), ('E5', 0.25), ('D5', 0.25),
            ('E5', 0.25), ('B4', 0.25), ('G4', 0.5),
            ('A4', 0.25), ('Bb4', 0.25), ('A4', 0.25), ('G4', 0.25),
            ('A4', 0.25), ('E4', 0.25), ('G4', 0.5),
        ]
        for _ in range(4):
            melody_notes += riff

        # Bass: driving A2 quarter notes
        bass_notes = [('A2', 1.0)] * 32

        # Percussion: noise on EVERY beat
        perc_notes = []
        for b in range(32):
            perc_notes.append(('A4', 0.12))
            perc_notes.append(('R',  0.88))

        v_melody = self._synth_voice(melody_notes, bpm, wave='square', vol=0.3)
        v_bass   = self._synth_voice(bass_notes,   bpm, wave='triangle', vol=0.4)
        v_perc   = self._synth_voice(perc_notes,   bpm, wave='noise', vol=0.22)

        mixed = self._mix_voices(v_melody, v_bass, v_perc)
        return _write_wav_bytes(mixed)

    # ── Music playback ────────────────────────────────────────────────────────

    def play_music(self, track: str) -> None:
        """Load and loop a music track by name. No-op if already playing."""
        if not self._ok or track == self._current_music:
            return
        path = self._music_files.get(track)
        if not path or not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)  # loop forever
            self._current_music = track
        except Exception:
            pass

    def stop_music(self) -> None:
        """Stop any playing music."""
        if not self._ok:
            return
        try:
            pygame.mixer.music.stop()
            self._current_music = None
        except Exception:
            pass

    def cleanup(self) -> None:
        """Remove temp music files on exit."""
        for path in self._music_files.values():
            try:
                os.unlink(path)
            except Exception:
                pass

    # ── Sound generators ──────────────────────────────────────────────────────

    def _make_laser(self) -> pygame.mixer.Sound:
        """Short zap: sine sweep 800→200 Hz over 0.1s, fade out."""
        duration = 0.1
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            freq = 800 - 600 * progress        # sweep 800→200
            phase = 2 * math.pi * freq * t
            amp = (1.0 - progress) * 0.4       # fade out
            samples.append(math.sin(phase) * amp)
        snd = _make(samples)
        snd.set_volume(0.35)
        return snd

    def _make_fire_shot(self) -> pygame.mixer.Sound:
        """Whoosh: noise + 200 Hz sine over 0.15s."""
        duration = 0.15
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            fade = 1.0 - progress
            noise = random.uniform(-1.0, 1.0) * 0.25
            tone = math.sin(2 * math.pi * 200 * t) * 0.2
            samples.append((noise + tone) * fade)
        snd = _make(samples)
        snd.set_volume(0.4)
        return snd

    def _make_magnetic_shot(self) -> pygame.mixer.Sound:
        """Low pulsing hum: 80 Hz sine modulated over 0.2s."""
        duration = 0.2
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            mod = 0.5 + 0.5 * math.sin(2 * math.pi * 12 * t)
            fade = 1.0 - progress
            tone = math.sin(2 * math.pi * 80 * t)
            tone += 0.3 * math.sin(2 * math.pi * 160 * t)
            samples.append(tone * mod * fade * 0.35)
        snd = _make(samples)
        snd.set_volume(0.35)
        return snd

    def _make_explosion_small(self) -> pygame.mixer.Sound:
        """Short noise burst 0.2s, fade out."""
        duration = 0.2
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            progress = i / n
            fade = (1.0 - progress) ** 1.5
            noise = random.uniform(-1.0, 1.0)
            t = i / SAMPLE_RATE
            tone = math.sin(2 * math.pi * 120 * t) * 0.3
            samples.append((noise * 0.7 + tone) * fade * 0.45)
        snd = _make(samples)
        snd.set_volume(0.4)
        return snd

    def _make_explosion_medium(self) -> pygame.mixer.Sound:
        """Longer noise burst 0.35s, deeper."""
        duration = 0.35
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            fade = (1.0 - progress) ** 1.3
            noise = random.uniform(-1.0, 1.0)
            tone = math.sin(2 * math.pi * 70 * t) * 0.4
            tone += math.sin(2 * math.pi * 140 * t) * 0.2
            samples.append((noise * 0.6 + tone) * fade * 0.45)
        snd = _make(samples)
        snd.set_volume(0.45)
        return snd

    def _make_explosion_large(self) -> pygame.mixer.Sound:
        """Deep boom: low sine + noise 0.5s."""
        duration = 0.5
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            if progress < 0.05:
                env = progress / 0.05
            else:
                env = (1.0 - progress) ** 1.2
            noise = random.uniform(-1.0, 1.0) * 0.5
            tone = math.sin(2 * math.pi * 45 * t) * 0.6
            tone += math.sin(2 * math.pi * 90 * t) * 0.2
            samples.append((noise + tone) * env * 0.45)
        snd = _make(samples)
        snd.set_volume(0.5)
        return snd

    def _make_powerup(self) -> pygame.mixer.Sound:
        """Ascending chime: three quick sine tones at 440, 550, 660 Hz."""
        note_dur = 0.08
        gap_dur  = 0.02
        freqs = [440, 550, 660]
        all_samples: list = []
        for freq in freqs:
            n = int(SAMPLE_RATE * note_dur)
            for i in range(n):
                t = i / SAMPLE_RATE
                progress = i / n
                fade = math.sin(math.pi * progress)
                all_samples.append(math.sin(2 * math.pi * freq * t) * fade * 0.4)
            gap_n = int(SAMPLE_RATE * gap_dur)
            all_samples.extend([0.0] * gap_n)
        snd = _make(all_samples)
        snd.set_volume(0.45)
        return snd

    def _make_player_hit(self) -> pygame.mixer.Sound:
        """Harsh buzz: 120 Hz square wave, 0.15s."""
        duration = 0.15
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            fade = 1.0 - progress
            phase = (t * 120) % 1.0
            sq = 1.0 if phase < 0.5 else -1.0
            noise = random.uniform(-0.3, 0.3)
            samples.append((sq * 0.7 + noise) * fade * 0.45)
        snd = _make(samples)
        snd.set_volume(0.4)
        return snd

    def _make_boss_warning(self) -> pygame.mixer.Sound:
        """Pulsing alarm: 440 Hz on/off pulses, 1.0s total."""
        duration = 1.0
        n = int(SAMPLE_RATE * duration)
        samples = []
        pulse_freq = 4.0
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            gate = 1.0 if math.sin(2 * math.pi * pulse_freq * t) > 0 else 0.0
            env = 1.0 if progress < 0.85 else (1.0 - progress) / 0.15
            tone = math.sin(2 * math.pi * 440 * t)
            tone += 0.5 * math.sin(2 * math.pi * 554 * t)
            samples.append(tone * gate * env * 0.3)
        snd = _make(samples)
        snd.set_volume(0.45)
        return snd

    def _make_boss_shoot(self) -> pygame.mixer.Sound:
        """Heavy thud: 60 Hz + noise burst, 0.25s."""
        duration = 0.25
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n
            if progress < 0.04:
                env = progress / 0.04
            else:
                env = (1.0 - progress) ** 1.4
            noise = random.uniform(-1.0, 1.0) * 0.4
            tone = math.sin(2 * math.pi * 60 * t) * 0.7
            tone += math.sin(2 * math.pi * 120 * t) * 0.2
            samples.append((noise + tone) * env * 0.45)
        snd = _make(samples)
        snd.set_volume(0.45)
        return snd

    # ── Public API ────────────────────────────────────────────────────────────

    def play(self, name: str) -> None:
        """Play a sound by name. Silently ignores errors."""
        if not self._ok:
            return
        try:
            snd = self._sounds.get(name)
            if snd:
                snd.play()
        except Exception:
            pass
