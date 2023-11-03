import time

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
from config_reader import config


class Spotify:

    _prefix = 'spotify:track:'
    _update_seconds = 5

    def __init__(self):
        self._client_id = config.spotify_client_id.get_secret_value()
        self._client_secret = config.spotify_client_secret.get_secret_value()
        self._spotify_username = config.spotify_username.get_secret_value()
        self._redirect_uri = config.spotify_redirect_uri.get_secret_value()
        self._spotify_search_client = spotipy.Spotify(client_credentials_manager=
                                                      SpotifyClientCredentials(client_id=self._client_id,
                                                                               client_secret=self._client_secret))
        self._spotify_read_playback_state = spotipy.Spotify(auth_manager=
                                                            SpotifyOAuth(scope="user-read-playback-state",
                                                                         client_id=self._client_id,
                                                                         client_secret=self._client_secret,
                                                                         redirect_uri=self._redirect_uri))
        self._spotify_modify_state_client = spotipy.Spotify(auth_manager=
                                                            SpotifyOAuth(scope="user-modify-playback-state",
                                                                         client_id=self._client_id,
                                                                         client_secret=self._client_secret,
                                                                         redirect_uri=self._redirect_uri))
        self._playback = self._spotify_read_playback_state.current_playback()
        self._last_playback_update = time.time()

    @staticmethod
    def __get_info(item) -> list[list[str]]:
        """
        collects artist, track, uri from search request and pack to list
        :param item:
        :return: list of lists of artist, track, uri
        """
        res = []
        for i in item["tracks"]["items"]:
            res.append([i["artists"][0]["name"], i["name"], i["uri"]])
        return res

    @staticmethod
    def get_raw_iru(uri: str):
        return uri[uri.rfind(":") + 1:]

    @staticmethod
    def get_full_uri(uri: str):
        if uri.find(Spotify._prefix) == -1:
            return Spotify._prefix + uri

    def force_update_playback(self):
        """
        updates playback client
        :return:
        """
        self._playback = self._spotify_read_playback_state.current_playback()

    def _update_playback(self):
        """
        updates playback client if cached time exceeded
        :return:
        """
        if abs(time.time() - self._last_playback_update) > self._update_seconds:
            self._playback = self._spotify_read_playback_state.current_playback()

    def _is_playing(self):
        return self._playback["is_playing"]

    def get_curr_track_name(self):
        self._update_playback()
        if self._playback is not None:
            return self._playback["item"]["name"]
        else:
            return None

    def get_curr_track_artists(self):
        self._update_playback()
        if self._playback is not None:
            artists = [artist["name"] for artist in self._playback["item"]["artists"]]
            return artists
        else:
            return None

    def get_curr_track(self, separator=' - '):
        self._update_playback()
        if self._playback is not None:
            return ', '.join([artist["name"] for artist in self._playback["item"]["artists"]]) + separator + self._playback["item"]["name"]
        else:
            return None

    def add_track_to_queue(self, uri: str):
        self._spotify_modify_state_client.add_to_queue(uri)

    def next_track(self):
        self._spotify_modify_state_client.next_track()
        self.force_update_playback()

    def previous_track(self):
        self._spotify_modify_state_client.previous_track()
        self.force_update_playback()

    def start_pause(self):
        self.force_update_playback()
        if self._is_playing():
            self._spotify_modify_state_client.pause_playback()
        else:
            self._spotify_modify_state_client.start_playback()
        self.force_update_playback()

    def search(self, request: str) -> list[list[str]]:
        """
        :param request: запрос
        :return: список с автором, названием
        """

        return self.__get_info(self._spotify_search_client.search(request))


spotify = Spotify()
