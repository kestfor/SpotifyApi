import asyncio
import time

import asyncspotify
import asyncspotify.http
from asyncspotify.client import get_id

from src.config_reader import config
from src.lyrics.lyrics import Lyrics, LyricsFinder
from src.spotify.db_auth import DatabaseAuth
from src.spotify.spotify_errors import *


class AsyncSpotify:
    class ModifiedHTTP(asyncspotify.http.HTTP):
        async def player_add_to_queue(self, uri: str, device_id):
            r = asyncspotify.Route('POST', f'me/player/queue?uri={uri}', device=device_id)
            await self.request(r)

        async def transfer_playback(self, device_id):
            r = asyncspotify.Route("PUT", "me/player")
            await self.request(r, json={"device_ids": [device_id]})

        async def start_playlist(self, uri, device_id):
            r = asyncspotify.Route("PUT", "me/player/play", device_id=device_id)
            await self.request(r, json={"context_uri": uri})

        async def get_curr_user_queue(self, device_id):
            r = asyncspotify.Route("GET", 'me/player/queue')
            return await self.request(r)

    class ModifiedClient(asyncspotify.client.Client):

        def __init__(self, auth):
            self.auth: DatabaseAuth = auth(self)
            self.http: AsyncSpotify.ModifiedHTTP = AsyncSpotify.ModifiedHTTP(self)

        async def authorize(self, url=None):
            await self.auth.authorize(url)

        async def player_add_to_queue(self, uri: str, device=None):
            await self.http.player_add_to_queue(uri, device_id=get_id(device))

        async def transfer_playback(self, device):
            await self.http.transfer_playback(device_id=get_id(device))

        async def get_player(self, **kwargs) -> asyncspotify.CurrentlyPlayingContext | None:
            data = await self.http.get_player(**kwargs)

            if data is not None:
                return asyncspotify.CurrentlyPlayingContext(self, data)

        async def get_curr_user_queue(self, device=None):
            data = await self.http.get_curr_user_queue(device_id=get_id(device))
            tracks = []
            for track_obj in data['queue']:
                tracks.append(asyncspotify.SimpleTrack(self, track_obj))
            return tracks

        async def start_playlist(self, uri: str, device=None):
            await self.http.start_playlist(uri=uri, device_id=get_id(device))

    # class ModifiedEasyAuthorizationCodeFlow(asyncspotify.EasyAuthorizationCodeFlow):
    #
    #     def __init__(self, client_id, client_secret, scope, storage):
    #         super().__init__(client_id=client_id, client_secret=client_secret, scope=scope, storage=storage)
    #
    #     async def authorize(self, url=None):
    #         '''Authorize the client. Reads from the file specificed by `store`.'''
    #
    #         data = await self.load()
    #
    #         # no data found, run first time setup
    #         # get response class, pass it to .store
    #         if data is None:
    #             if url is None:
    #                 raise spotify_errors.AuthorizationError
    #             data = await self.setup(url)
    #
    #             if isinstance(data, AuthenticationResponse):
    #                 await self.store(data)
    #
    #         if not isinstance(data, AuthenticationResponse):
    #             raise TypeError('setup() has to return an AuthenticationResponse')
    #
    #         self._data = data
    #
    #         # refresh it now if it's expired
    #         if self._data.is_expired():
    #             await self.refresh(start_task=True)
    #         else:
    #             # manually start refresh task if we didn't refresh on startup
    #             self.refresh_in(self._data.seconds_until_expire())
    #
    #     def access_token(self):
    #         return self._data.access_token
    #
    #     async def setup(self, url):
    #
    #         code_url = url
    #
    #         src = self.get_code_from_redirect(code_url)
    #         d = self.create_token_data_from_code(src)
    #
    #         data = await self._token(d)
    #         return self.response_class(data)

    _track_prefix = 'spotify%3Atrack%3A'
    _album_prefix = 'spotify:album:'
    _playlist_prefix = 'spotify:playlist:'
    _artist_prefix = 'spotify:artist:'
    _update_timeout = 5
    _volume_step = 5

    def __init__(self):
        self._client_id = config.spotify_client_id.get_secret_value()
        self._client_secret = config.spotify_client_secret.get_secret_value()
        self._spotify_username = config.spotify_username.get_secret_value()
        self._redirect_uri = config.spotify_redirect_uri.get_secret_value()
        self._scope = asyncspotify.Scope(user_modify_playback_state=True, user_read_playback_state=True)
        self._token_file = config.token_file.get_secret_value()
        self._lyrics_finder = LyricsFinder()
        self._last_song_lyrics: Lyrics | None = None

        self._auth = DatabaseAuth(
            client_id=self._client_id,
            client_secret=self._client_secret,
            scope=self._scope,
        )
        self._auth.redirect_uri = self._redirect_uri

        self._session = AsyncSpotify.ModifiedClient(self._auth)
        self._volume = 50
        self._saved_volume = self._volume
        self._playing: bool = False
        self._cached_currently_playing: asyncspotify.CurrentlyPlaying | None = None
        self._last_update_time = 0
        self._authorized = False

    async def create_authorize_route(self) -> str:
        return self._session.auth.create_authorize_route()

    async def authorize(self, storage_id=None):
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
        self._authorized = False

    async def force_update(self):
        try:
            self._cached_currently_playing = await self._session.player_currently_playing()
        except:
            raise ConnectionError

    async def update(self):
        now = time.time()
        if (now - self._last_update_time) >= self._update_timeout:
            await self.force_update()

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
    def get_full_uri(uri: str):
        if uri.find(AsyncSpotify._track_prefix) == -1:
            return AsyncSpotify._track_prefix + uri

    async def get_curr_track(self):
        try:
            await self.update()
            currently_playing = self._cached_currently_playing
            curr_track = currently_playing.track
            artists = [artist.name for artist in curr_track.artists]
            name = curr_track.name
            return [artists, name]
        except:
            raise ConnectionError

    async def get_lyrics(self, func_waiter=None, **func_waiter_kwargs):
        artists, name = await self.get_curr_track()
        main_author = artists[0]
        name = name[:name.find('(')] if '(' in name else name
        name = name.strip()
        if self._last_song_lyrics:
            cached_artist, cached_song = self._last_song_lyrics.artist.lower(), self._last_song_lyrics.name.lower()
            if main_author.lower() == cached_artist and cached_song == name.lower():
                return self._last_song_lyrics
            else:
                if func_waiter is not None:
                    await func_waiter(**func_waiter_kwargs)
                self._last_song_lyrics = await self._lyrics_finder.find(main_author, name)
                return self._last_song_lyrics
        else:
            if func_waiter is not None:
                await func_waiter(**func_waiter_kwargs)
            self._last_song_lyrics = await self._lyrics_finder.find(main_author, name)
            return self._last_song_lyrics

    async def add_track_to_queue(self, uri):
        try:
            if self._track_prefix not in uri:
                uri = self._track_prefix + uri
            await self._session.player_add_to_queue(uri)
        except asyncspotify.Forbidden:
            raise PremiumRequired
        except:
            raise ConnectionError

    async def get_curr_user_queue(self) -> list[asyncspotify.SimpleTrack]:
        try:
            queue = await self._session.get_curr_user_queue()

            #await self.synchronize_queue()

            return queue
        except asyncspotify.Forbidden:
            raise PremiumRequired
        except:
            raise ConnectionError

    async def get_formatted_curr_user_queue(self) -> list[str]:
        queue = await self.get_curr_user_queue()
        res = []
        for item in queue:
            res.append(item.name + ' - ' + ', '.join([artist.name for artist in item.artists]))
        return res

    async def next_track(self):
        try:
            await self._session.player_next()
            self._playing = True
            await self.force_update()
        except asyncspotify.Forbidden:
            raise PremiumRequired
        except:
            raise ConnectionError

    async def previous_track(self):
        try:
            await self._session.player_prev()
            self._playing = True
            await self.force_update()
        except asyncspotify.Forbidden:
            raise PremiumRequired
        except:
            raise ConnectionError

    async def start_pause(self):
        try:
            currently_playing = await self._session.player_currently_playing()
            if currently_playing.is_playing:
                self._playing = False
                await self._session.player_pause()
            else:
                self._playing = True
                await self._session.player_play()
        except asyncspotify.Forbidden:
            raise PremiumRequired
        except:
            raise ConnectionError

    async def increase_volume(self):
        try:
            await self._session.player_volume(min(100, self._volume + self._volume_step))
        except asyncspotify.Forbidden:
            pass
        else:
            self._volume = min(100, self._volume + self._volume_step)

    async def decrease_volume(self):
        try:
            await self._session.player_volume(max(0, self._volume - self._volume_step))
        except asyncspotify.Forbidden:
            pass
        else:
            self._volume = max(0, self._volume - self._volume_step)

    async def get_devices(self) -> list[asyncspotify.Device]:
        devices = await self._session.get_devices()
        return devices

    async def transfer_player(self, device: str | asyncspotify.Device):
        try:
            await self._session.transfer_playback(device)
            await asyncio.sleep(1)
            await self._session.player_volume(self._volume)
        except:
            raise ConnectionError

    # TODO implement
    async def synchronize_queue(self):
        """shift queue top to current song"""
        raise NotImplementedError('synchronize_queue')

    async def mute_unmute(self):
        old_values = [self._volume, self._saved_volume]
        try:
            if self._volume == 0:
                self._volume = self._saved_volume
            else:
                self._saved_volume = self._volume
                self._volume = 0
            await self._session.player_volume(self._volume)
        except asyncspotify.Forbidden:
            self._volume, self._saved_volume = old_values
            raise Forbidden

    @property
    def volume(self):
        return self._volume

    @property
    def is_playing(self):
        return self._playing

    async def search(self, request: str) -> list[list[str]]:
        """
        :param request: запрос
        :return: список с id, автором, названием
        """
        try:
            return await self.__get_info(await self._session.search("track", q=request, limit=10))
        except:
            raise ConnectionError
