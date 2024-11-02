import asyncio
import functools
import time

import asyncspotify
import asyncspotify.http

from src.env import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from src.lyrics.lyrics import Lyrics, LyricsFinder
from src.spotify.db_auth import DatabaseAuth
from src.spotify.modified_client import ModifiedClient
from src.spotify.spotify_errors import *
from src.spotify.track_in_queue import TrackInQueue, TrackWithUser


class AsyncSpotify:
    _track_prefix = 'spotify%3Atrack%3A'
    _album_prefix = 'spotify:album:'
    _playlist_prefix = 'spotify:playlist:'
    _artist_prefix = 'spotify:artist:'
    _update_timeout = 5
    _volume_step = 5

    @staticmethod
    async def __get_info(item) -> list[list[str]]:
        """
        collects artist, track, uri from search request and pack to list
        :param item:
        :return: list of lists of artist, track, uri
        """
        res = []
        for i in item["tracks"]:
            res.append([i.artists[0].name, i.name, i.id])
        return res

    @staticmethod
    def error_wrapper():
        def wrapper(function):
            @functools.wraps(function)
            async def wrapped(*args, **kwargs):
                try:
                    res = await function(*args, **kwargs)
                except asyncspotify.Forbidden:
                    raise PremiumRequired
                except Exception:
                    raise ConnectionError
                return res

            return wrapped

        return wrapper

    @staticmethod
    def get_full_uri(uri: str):
        if uri.find(AsyncSpotify._track_prefix) == -1:
            return AsyncSpotify._track_prefix + uri

    def __init__(self):
        self._client_id = SPOTIFY_CLIENT_ID
        self._client_secret = SPOTIFY_CLIENT_SECRET
        self._scope = asyncspotify.Scope(user_modify_playback_state=True, user_read_playback_state=True)
        self._lyrics_finder = LyricsFinder()
        self._last_song_lyrics: Lyrics | None = None

        self._auth = DatabaseAuth(
            client_id=self._client_id,
            client_secret=self._client_secret,
            scope=self._scope,
        )
        self._auth.redirect_uri = SPOTIFY_REDIRECT_URI

        self._session = ModifiedClient(self._auth)
        self._volume = 50
        self._saved_volume = self._volume
        self._playing: bool = False
        self._cached_currently_playing: asyncspotify.CurrentlyPlaying | None = None
        self._last_update_time = 0
        self._authorized = False
        self._closed = False

        self._users_queue: list[TrackInQueue] = []

    @property
    def authorized(self) -> bool:
        return self._authorized

    @property
    def closed(self) -> bool:
        return self._closed

    async def create_authorize_route(self) -> str:
        return self._session.auth.create_authorize_route()

    def deauthorize(self):
        self._authorized = False

    async def authorize(self, storage_id):
        if not self._authorized:
            await self._session.authorize(storage_id)
        try:
            player = await self._session.get_player()
            device = player.device
            self._playing = player.is_playing
            self._volume = device.volume_percent
            self._saved_volume = self._volume
            self._authorized = True
        except Exception as e:
            print(e)
        except asyncspotify.exceptions.NotFound:
            raise ConnectionError("there is no active device")

    async def is_active(self):
        try:
            await self._session.player_currently_playing()
            return True
        except:
            return False

    async def start_playlist(self, url: str):
        if not url.startswith("https://open.spotify.com/"):
            raise ValueError
        url = url[0:url.find('?')]
        splited = url.split('/')
        type, id = splited[-2], splited[-1]
        if type == 'album':
            uri = AsyncSpotify._album_prefix + id
        elif type == 'playlist':
            uri = AsyncSpotify._playlist_prefix + id
        elif type == 'artist':
            uri = AsyncSpotify._artist_prefix + id
        else:
            raise ValueError("wrong url")
        await self._session.start_playlist(uri)

    async def close(self):
        await self._session.close()
        self._closed = True
        self._authorized = False

    @error_wrapper()
    async def force_update(self):
        self._cached_currently_playing = await self._session.player_currently_playing()

    @error_wrapper()
    async def update(self):
        now = time.time()
        if (now - self._last_update_time) >= self._update_timeout:
            await self.force_update()

    @error_wrapper()
    async def get_curr_track(self) -> tuple[list[str], str]:
        """
        get authors as str list and track name
        """
        await self.update()
        currently_playing = self._cached_currently_playing
        curr_track = currently_playing.track
        artists = [artist.name for artist in curr_track.artists]
        name = curr_track.name
        return artists, name

    @error_wrapper()
    async def get_lyrics(self):
        artists, name = await self.get_curr_track()
        main_author = artists[0]
        name = name[:name.find('(')] if '(' in name else name
        name = name.strip()
        if self._last_song_lyrics:
            cached_artist, cached_song = self._last_song_lyrics.artist.lower(), self._last_song_lyrics.name.lower()
            if main_author.lower() == cached_artist and cached_song == name.lower():
                return self._last_song_lyrics
            else:
                self._last_song_lyrics = await self._lyrics_finder.find(main_author, name)
                return self._last_song_lyrics
        else:
            self._last_song_lyrics = await self._lyrics_finder.find(main_author, name)
            return self._last_song_lyrics

    @error_wrapper()
    async def add_track_to_queue(self, username: str, uri: str):
        if self._track_prefix not in uri:
            uri = self._track_prefix + uri
        await self._session.player_add_to_queue(uri)
        self._users_queue.append(TrackInQueue(username, uri))

    def _sync_queue(self, spotify_queue: list[asyncspotify.SimpleTrack]):
        start_index = -1
        first_spotify_track = spotify_queue[0]
        for index in range(len(self._users_queue)):
            if self._users_queue[index].track_uri == first_spotify_track.uri:
                start_index = index
                break
        if start_index == -1:
            self._users_queue = []
        else:
            self._users_queue = self._users_queue[start_index:]

    @error_wrapper()
    async def get_curr_user_queue(self) -> list[TrackWithUser]:
        if len(self._users_queue) == 0:
            return []

        queue = await self._session.get_curr_user_queue()
        self._sync_queue(queue)
        return [TrackWithUser(self._users_queue[i].author_username, queue[i]) for i in
                range(len(self._users_queue))]

    async def get_formatted_curr_user_queue(self) -> list[str]:
        queue: list[TrackWithUser] = await self.get_curr_user_queue()
        res = []
        for item in queue:
            res.append(item.track.name + ' - ' + ', '.join([artist.name for artist in item.track.artists]))
        return res

    @error_wrapper()
    async def next_track(self):
        await self._session.player_next()
        self._playing = True
        await self.force_update()

    @error_wrapper()
    async def previous_track(self):
        await self._session.player_prev()
        self._playing = True
        await self.force_update()

    @error_wrapper()
    async def start_pause(self):
        currently_playing = await self._session.player_currently_playing()
        if currently_playing.is_playing:
            self._playing = False
            await self._session.player_pause()
        else:
            self._playing = True
            await self._session.player_play()

    @error_wrapper()
    async def increase_volume(self):
        await self._session.player_volume(min(100, self._volume + self._volume_step))
        self._volume = min(100, self._volume + self._volume_step)

    @error_wrapper()
    async def decrease_volume(self):
        await self._session.player_volume(max(0, self._volume - self._volume_step))
        self._volume = max(0, self._volume - self._volume_step)

    @error_wrapper()
    async def get_devices(self) -> list[asyncspotify.Device]:
        return await self._session.get_devices()

    @error_wrapper()
    async def transfer_player(self, device: str | asyncspotify.Device):
        await self._session.transfer_playback(device)
        await asyncio.sleep(1)
        await self._session.player_volume(self._volume)

    #TODO здесь лажа какая-то, метод не работает
    @error_wrapper()
    async def mute_unmute(self):
        if self._volume == 0:
            await self._session.player_volume(self._saved_volume)
            self._volume = self._saved_volume
        else:
            await self._session.player_volume(0)
            self._saved_volume = self._volume
            self._volume = 0

    @property
    def volume(self):
        return self._volume

    @property
    def is_playing(self):
        return self._playing

    @error_wrapper()
    async def search(self, request: str) -> list[list[str]]:
        """
        :param request: запрос
        :return: список с id, автором, названием
        """
        return await self.__get_info(await self._session.search("track", q=request, limit=10))
