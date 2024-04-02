from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel

from app.db import lifespan


app = FastAPI(lifespan=lifespan)


class Waterbody(BaseModel):
    uid: str
    wb_id: int
    area_m2: float


@app.get("/waterbody/{wb_id}")
async def get_waterbody(wb_id: int, request: Request) -> Waterbody:
    """
    Gets the metadata of a specific waterbody based on its id
    """
    async with request.app.async_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT uid, wb_id, area_m2 "
                "FROM waterbodies_historical_extent "
                f"WHERE wb_id={wb_id}"
            )
            waterbody = await cur.fetchone()
            if waterbody is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Waterbody not found"
                )
            uid, wb_id, area_m2 = waterbody
            return Waterbody(uid=uid, wb_id=wb_id, area_m2=area_m2)


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

