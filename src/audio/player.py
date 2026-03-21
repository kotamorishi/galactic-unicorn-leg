"""Audio player that plays sound presets via HAL AudioInterface."""

from audio.presets import get_preset


class AudioPlayer:

    def __init__(self, audio_hal):
        self._audio = audio_hal

    def init(self):
        self._audio.init()

    async def play_preset(self, preset_id, volume_percent=50):
        """Play a sound preset by ID.

        Args:
            preset_id: Preset ID (1-20)
            volume_percent: Volume 0-100
        """
        preset = get_preset(preset_id)
        if preset is None:
            return
        self._audio.set_volume(volume_percent / 100.0)
        await self._audio.play_sequence(preset["notes"])

    def stop(self):
        self._audio.stop()
