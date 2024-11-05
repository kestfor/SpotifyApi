from typing import Optional

from asyncspotify import Client, CurrentlyPlayingContext, Device, HTTPException

from src.spotify.spotify_errors import UnsupportedDevice


class SpotifyPlayer:

    @staticmethod
    async def get_player(session: Client) -> 'SpotifyPlayer':
        player = SpotifyPlayer(session)
        player._spotify_player = await session.get_player()
        player._device = player._spotify_player.device
        return player

    def _mute_unmute_generator(self):
        was = self._device.volume_percent
        now = 0 if was > 0 else 50
        while True:
            yield now
            was, now = self._device.volume_percent, was

    def __init__(self, session: Client):
        self._session = session
        self._spotify_player: Optional[CurrentlyPlayingContext] = None
        self._device: Optional[Device] = None
        self._volume_step = 5
        self._gen = self._mute_unmute_generator()

    async def mute_unmute(self):
        try:
            self._device.volume_percent = next(self._gen)
        except HTTPException:
            raise UnsupportedDevice()

    async def set_volume(self, volume: int):
        try:
            await self._spotify_player.volume(volume)
        except HTTPException:
            raise UnsupportedDevice()

    @property
    def volume(self):
        return self._device.volume_percent

    @property
    def is_playing(self):
        return self._device.is_active

    async def next_track(self):
        await self._spotify_player.next()

    async def previous_track(self):
        await self._spotify_player.prev()

    async def start_pause(self):
        currently_playing = await self._session.player_currently_playing()
        if currently_playing.is_playing:
            self._device.is_active = False
            await self._spotify_player.pause()
        else:
            self._device.is_active = True
            await self._spotify_player.play()

    async def increase_volume(self):
        volume = self._device.volume_percent
        new_volume = min(100, volume + self._volume_step)
        try:
            await self._session.player_volume(new_volume, self._device.id)
            self._device.volume_percent = new_volume
        except HTTPException:
            raise UnsupportedDevice()

    async def decrease_volume(self):
        volume = self._device.volume_percent
        new_volume = max(0, volume - self._volume_step)
        try:
            await self._session.player_volume(new_volume, self._device.id)
            self._device.volume_percent = new_volume
        except HTTPException:
            raise UnsupportedDevice()
