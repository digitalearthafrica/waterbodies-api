from datetime import date
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from geojson_pydantic import Feature
from pydantic import BaseModel
from typing import AsyncGenerator

from app.db import lifespan
from app.queries import waterbody_observations_query


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
        request: Request,
        wb_id: int,
        start_date: date,
        end_date: date
    ) -> AsyncGenerator[str, None]:
    """ Async generator that yields a string (formatted as a CSV line) for each
    row returned by the SQL query as the query is being run.
    """
    # Before running the query, yield the csv header
    yield "date,area_wet_m2,percent_wet,area_dry_m2,percent_dry,area_invalid_m2,percent_invalid,area_observed_m2,percent_observed\n"

    # Perform the query
    query = waterbody_observations_query(wb_id, start_date, end_date)

    async with request.app.async_pool.connection() as conn:
        async with conn.cursor() as cursor:
            async for wb_observation in cursor.stream(query):
                # TODO - any changes to the query above need to be reflected here
                obs_date, obs_area_wet, obs_pc_wet, obs_area_dry, obs_pc_dry, obs_area_invalid, obs_pc_invalid, obs_area, obs_pc = wb_observation
                csv_line = f"{str(obs_date.strftime('%Y-%m-%d'))},{obs_area_wet},{obs_pc_wet:.2f},{obs_area_dry},{obs_pc_dry:.2f},{obs_area_invalid},{obs_pc_invalid:.2f},{obs_area},{obs_pc:.2f}\n"
                yield csv_line


@app.get("/waterbody/{wb_id}/observations/csv")
async def get_waterbody_observations_csv(
        request: Request,
        wb_id: int,
        start_date: date = date.min,
        end_date: date = date.max
    ) -> StreamingResponse:
    """
    Returns the water body observations over time in a CSV format
    """
    # First we do a quick check if the waterbody exists, and if not send
    # a 404 response. If it does exist then run the query to get the
    # waterbody observations. This allows the client to determine if the
    # waterbody exists and has no data (in the query date range), or it
    # doesn't exist at all.
    async with request.app.async_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT wb_id "
                "FROM waterbodies_historical_extent "
                f"WHERE wb_id={wb_id}"
            )
            waterbody = await cur.fetchone()
            if waterbody is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Waterbody not found"
                )

            # Stream the reponse data, this means we don't need to keep a full copy
            # of the water observations in memeory, and we can start writing the
            # response as soon as the first row is read from the DB
            return StreamingResponse(
                query_waterbody_observations(request, wb_id, start_date, end_date),
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

