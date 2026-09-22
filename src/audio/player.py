"""Audio player that plays sound presets via HAL AudioInterface."""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from audio.presets import get_preset


class AudioPlayer:

    def __init__(self, audio_hal):
        self._audio = audio_hal

    def init(self):
        self._audio.init()

    async def play_preset(self, preset_id, volume_percent=50, count=1, gap_ms=1000):
        """Play a sound preset by ID.

        Args:
            preset_id: Preset ID (1-20)
            volume_percent: Volume 0-100
            count: Number of times to play the preset (>= 1)
            gap_ms: Pause between repeats in milliseconds (ignored when count == 1)
        """
        preset = get_preset(preset_id)
        if preset is None:
            return
        self._audio.set_volume(volume_percent / 100.0)
        for i in range(count):
            await self._audio.play_sequence(preset["notes"])
            if i < count - 1:
                await asyncio.sleep(gap_ms / 1000)

    def stop(self):
        self._audio.stop()
