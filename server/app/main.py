from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.db import lifespan


app = FastAPI(lifespan=lifespan)


class CheckConnectionResult(BaseModel):
    connected: bool


@app.get("/check-connection")
async def check_connection(request: Request) -> CheckConnectionResult:
    """
    Runs a very simple select statement on the database to
    check if it is connected
    """
    async with request.app.async_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            await cur.fetchall()
            # if we make it here without error, then the application
            # is connected to the database
            return CheckConnectionResult(connected=True)

