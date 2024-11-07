import datetime
import hashlib
from typing import Annotated
import fastapi
import uvicorn
from aiohttp import ClientSession
from fastapi import Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.env import SPOTIFY_REDIRECT_URI, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from src.sql.engine import get_session
from src.sql.models.auth import Auth
from src.sql.models.user import User

app = fastapi.FastAPI()


@app.get("/callback")
async def auth_callback(code: str, session: Annotated[AsyncSession, Depends(get_session)]):
    tg_redirect_url = "https://t.me/SpotifyShareControlBot?start=_auth_"

    body = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }

    async with ClientSession() as client_session:
        response = await client_session.post("https://accounts.spotify.com/api/token", data=body)

        if response.status == 200:
            data = await response.json()
            created_at = datetime.datetime.now(datetime.timezone.utc)

            data['created_at'] = created_at
            data["expires_at"] = created_at + datetime.timedelta(seconds=data["expires_in"])

            new_auth = Auth(**data)
            session.add(new_auth)
            await session.flush()
            new_auth.hash = hashlib.sha1(new_auth.id.to_bytes(8, "big")).hexdigest()

            return RedirectResponse(f'{tg_redirect_url}{new_auth.hash}')
        else:
            print(response.status, response.reason)
            print("error occured")
            return RedirectResponse(tg_redirect_url)


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=80)


