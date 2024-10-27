from asyncspotify import AuthorizationCodeFlow, Scope
from asyncspotify.oauth.response import AuthorizationCodeFlowResponse
from sqlalchemy.dialects.mysql import insert

from src.spotify.spotify_errors import *
from src.sql.engine import async_session
from src.sql.tables import Auth


class DatabaseAuth(AuthorizationCodeFlow):

    def __init__(self, client_id, client_secret, storage_id: int = None, scope=Scope.none(),
                 response_class=AuthorizationCodeFlowResponse):
        super().__init__(client_id, client_secret, scope, 'http://localhost/', response_class)
        self._storage_id = storage_id

    async def authorize(self, storage_id=None):
        data = await self.load(storage_id)
        self._data = data

        # refresh it now if it's expired
        if self._data.is_expired():
            await self.refresh(start_task=True)
        else:
            # manually start refresh task if we didn't refresh on startup
            self.refresh_in(self._data.seconds_until_expire())

    async def setup(self, storage_id=None):
        return await self.load(storage_id)

    @property
    def storage_id(self):
        return self._storage_id

    @storage_id.setter
    def storage_id(self, value):
        self._storage_id = value

    async def load(self, storage_id=None):
        self._storage_id = storage_id
        """load data from database"""

        if self._storage_id is None:
            raise AuthorizationError("storage_id is required")

        async with async_session() as session, session.begin():
            data: Auth = await session.get(Auth, self._storage_id)
            if data is not None:
                return self.response_class.from_data(data.as_dict())

    async def store(self, response):
        """simply store the response to db"""
        async with async_session() as session, session.begin():
            data = response.to_dict()
            data["id"] = self._storage_id
            insert_stmt = insert(Auth).values(**data)
            on_dupl_stmt = insert_stmt.on_duplicate_key_update(insert_stmt.inserted)
            await session.execute(on_dupl_stmt)

    def access_token(self):
        return self._data.access_token
