import datetime
from typing import Annotated

import fastapi
import uvicorn
from aiohttp import ClientSession
from fastapi import Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.sql.engine import get_session
from src.sql.tables import Auth

app = fastapi.FastAPI()

CLIENT_ID = "e76571fbbd914d1b9dadbca52f72a38b"
CLIENT_SECRET = "0c99922335eb4fb7b4ee3f0b83088c43"


@app.get("/callback")
async def auth_callback(code: str, session: Annotated[AsyncSession, Depends(get_session)]):
    tg_redirect_url = "https://t.me/SpotifyShareControlBot?start=_auth_"

    body = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:80/callback",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    async with ClientSession() as client_session:
        response = await client_session.post("https://accounts.spotify.com/api/token", data=body)

        if response.status == 200:
            print("Authorization src received")
            data = await response.json()
            print(data)
            created_at = datetime.datetime.now()

            data['created_at'] = created_at
            data["expires_at"] = created_at + datetime.timedelta(seconds=data["expires_in"])

            async with session.begin():
                new_auth = Auth(**data)
                session.add(new_auth)
                await session.flush()

            return RedirectResponse(f'{tg_redirect_url}{new_auth.id}')
        else:
            print(response.status, response.reason)
            print("error occured")
            return RedirectResponse(tg_redirect_url)


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=80)
