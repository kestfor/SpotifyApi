import hashlib
import logging

from asyncspotify import AuthorizationCodeFlow, Scope
from asyncspotify.oauth.response import AuthorizationCodeFlowResponse
from sqlalchemy.dialects.mysql import insert

from src.spotify.spotify_errors import *
from src.sql.engine import async_session, get_session
from src.sql.models.auth import Auth


class DatabaseAuth(AuthorizationCodeFlow):

    def __init__(self, client_id, client_secret, redirect_uri: str = "http://localhost/", storage_id: int = None,
                 scope=Scope.none(),
                 response_class=AuthorizationCodeFlowResponse):
        super().__init__(client_id, client_secret, scope, redirect_uri, response_class)
        self._storage_id = storage_id

    async def authorize(self):
        data = await self.load()
        self._data = data

        # refresh it now if it's expired
        if self._data.is_expired():
            await self.refresh(start_task=True)
        else:
            # manually start refresh task if we didn't refresh on startup
            self.refresh_in(self._data.seconds_until_expire())

    async def setup(self):
        return await self.load()

    @property
    def storage_id(self):
        return self._storage_id

    @storage_id.setter
    def storage_id(self, value):
        self._storage_id = value

    async def load(self):
        """load data from database"""

        if self._storage_id is None:
            raise AuthorizationError("storage_id is required")

        async with async_session() as session, session.begin():
            data: Auth = await session.get(Auth, self._storage_id)
            if data is not None:
                return self.response_class.from_data(data.as_dict())

    async def store(self, response):
        if self._storage_id is None:
            raise AuthorizationError("storage_id is required")
        """simply store the response to db"""
        try:
            async with get_session() as session:
                data = response.to_dict()
                data["id"] = self._storage_id
                data["hash"] = hashlib.sha1(self._storage_id.to_bytes(8, "big")).hexdigest()
                insert_stmt = insert(Auth).values(**data)
                on_dupl_stmt = insert_stmt.on_duplicate_key_update(insert_stmt.inserted)
                await session.execute(on_dupl_stmt)
                await session.flush()

        except Exception as e:
            logging.critical(e)

    def access_token(self):
        return self._data.access_token
