import asyncspotify
from asyncspotify.client import get_id

from src.spotify.db_auth import DatabaseAuth
from src.spotify.modified_http import ModifiedHTTP


class ModifiedClient(asyncspotify.client.Client):

    def __init__(self, auth):
        self.auth: DatabaseAuth = auth(self)
        self.http: ModifiedHTTP = ModifiedHTTP(self)

    async def authorize(self):
        await self.auth.authorize()

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
