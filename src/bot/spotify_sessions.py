from sqlalchemy.ext.asyncio import AsyncSession

from src.spotify.spotify import AsyncSpotify
from src.spotify.spotify_errors import AuthorizationError
from src.sql.models.user import User


class SpotifySessions:

    def __init__(self):
        self._sessions: dict[int, AsyncSpotify] = {}

    async def get_or_create(self, user: User, session: AsyncSession) -> AsyncSpotify:
        master = await user.get_master(session)
        if not master:
            master = user

        auth_id = master.auth_id

        if auth_id is None:
            raise AuthorizationError(f"user {master} was not authorized")

        if master.user_id not in self._sessions:
            self._sessions[master.user_id] = AsyncSpotify(auth_id)

        spotify = self._sessions[master.user_id]
        if not spotify.authorized:
            await spotify.authorize()
        return spotify

    async def clear_spotify(self, user_id):

        spotify = self._sessions.pop(user_id, None)
        if spotify is not None and not spotify.closed:
            await spotify.close()


spotify_sessions = SpotifySessions()
