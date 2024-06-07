from datetime import date
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

    start_date_str = start_date.strftime("%04Y-%m-%d")
    end_date_str = end_date.strftime("%04Y-%m-%d")

    # Perform the query
    query = (
        "WITH waterbody_stats AS ("
        "    SELECT"
        "        wbo.date,"
        "        SUM(wbo.area_wet_m2) AS area_wet,"
        "        SUM(wbo.area_dry_m2) AS area_dry,"
        "        SUM(wbo.area_invalid_m2) AS area_invalid,"
        "        SUM(wbo.area_wet_m2 + wbo.area_dry_m2 + wbo.area_invalid_m2) AS observed_area,"
        "        wb.area_m2"
        "    FROM "
        "        waterbodies_observations AS wbo "
        "    JOIN "
        "        waterbodies_historical_extent AS wb ON wbo.uid = wb.uid "
        "    WHERE "
        f"        wb.wb_id = {wb_id}"
        f"        AND wbo.date BETWEEN '{start_date_str}' AND '{end_date_str}'"
        "    GROUP BY "
        "        wbo.date, wb.area_m2"
        "),"
        "filtered_stats AS ("
        "    SELECT"
        "        date,"
        "        area_wet,"
        "        area_wet / area_m2 AS pc_wet,"
        "        area_dry,"
        "        area_dry / area_m2 AS pc_dry,"
        "        area_invalid,"
        "        area_invalid / area_m2 AS pc_invalid,"
        "        observed_area,"
        "        observed_area / area_m2 AS observed_area_proportion"
        "    FROM "
        "        waterbody_stats"
        "    WHERE"
        "        observed_area / area_m2 > 0.85 AND area_invalid / area_m2 < 0.1"
        ")"
        "SELECT * FROM filtered_stats"
    )
    async with request.app.async_pool.connection() as conn:
        async with conn.cursor() as cursor:
            async for wb_observation in cursor.stream(query):
                # TODO - any changes to the query above need to be reflected
                # here
                #obs_date, obs_area_wet, obs_pc_wet, obs_area_dry, obs_pc_dry, obs_area_invalid, obs_pc_invalid, obs_area, obs_area_proportion = wb_observation
                #csv_line = f"{str(obs_date.strftime('%Y-%m-%d'))},{obs_area_wet},{100*obs_pc_wet:.2f},{obs_area_dry},{100*obs_pc_dry:.2f},{obs_area_invalid},{100*obs_pc_invalid:.2f},{obs_area},{100*obs_area_proportion:.2f}\n"
                csv_line = f"{start_date},{end_date},{start_date_str},{end_date_str}\n"
                yield csv_line


@app.get("/waterbody/{wb_id}/observations/csv")
async def get_waterbody_observations_csv(
        request: Request,
        wb_id: int,
        start_date: date,
        end_date: date
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

