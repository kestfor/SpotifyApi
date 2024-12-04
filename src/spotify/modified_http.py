import asyncspotify


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
