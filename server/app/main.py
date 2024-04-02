from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from geojson_pydantic import Feature
from pydantic import BaseModel
from typing import AsyncGenerator

from app.db import lifespan


app = FastAPI(lifespan=lifespan)

# Allow all origins, and all methods
# Without this CORS may block other systems attempting to
# access these web services
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# defines structure of data returned by waterbody metadata handler
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


async def query_waterbody_observations(
        request: Request, wb_id: int
    ) -> AsyncGenerator[str, None]:
    """ Async generator that yields a string (formatted as a CSV line) for each
    row returned by the SQL query as the query is being run.
    """
    # TODO - updated this query to something useful
    query = (
        "SELECT date, px_wet "
        "FROM waterbody_observations AS wo "
        "JOIN waterbodies_historical_extent AS whe "
        "    ON wo.uid = whe.uid "
        f"WHERE wb_id={wb_id}"
    )
    async with request.app.async_pool.connection() as conn:
        async with conn.cursor() as cursor:
            async for wb_observation in cursor.stream(query):
                # TODO - any changes to the query above need to be reflected
                # here
                obs_date, obs_px_wet = wb_observation
                csv_line = f"{str(obs_date)},{obs_px_wet}\n"
                yield csv_line


@app.get("/waterbody/{wb_id}/observations/csv")
async def get_waterbody_observations_csv(
        wb_id: int,
        request: Request
    ) -> StreamingResponse:
    """
    Returns the water body observations over time in a CSV format
    """
    # Stream the reponse data, this means we don't need to keep a full copy
    # of the water observations in memeory, and we can start writing the
    # response as soon as the first row is read from the DB
    return StreamingResponse(
        query_waterbody_observations(request, wb_id),
        media_type='text/csv'
    )


@app.get("/waterbody/{wb_id}/geometry")
async def get_waterbody_geometry(wb_id: int, request: Request) -> Feature:
    """
    Gets the geometry (geojson) of a specific waterbody based on its id
    """
    async with request.app.async_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT "
                "jsonb_build_object( "
                "    'type', 'Feature', "
                "    'id', wb_id, "
                "    'geometry', ST_AsGeoJSON(geometry)::jsonb, "
                "    'properties', jsonb_build_object('id', wb_id) "
                ") as geojson "
                "FROM waterbodies_historical_extent "
                f"WHERE wb_id={wb_id}"
            )
            waterbody_geom = await cur.fetchone()
            if waterbody_geom is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Waterbody not found"
                )
            return waterbody_geom[0]


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

