import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool


def get_connection_str() -> str:
    """
    Returns a keyword=value space separated list of the connection
    details for the postgres database. Details on the spec of this
    string can be found at
    https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
    """
    return (
        f"dbname={os.getenv('POSTGRES_DB')} "
        f"user={os.getenv('POSTGRES_USER')} "
        f"password={os.getenv('POSTGRES_PASSWORD')} "
        f"host={os.getenv('POSTGRES_HOST')} "
        f"port={os.getenv('POSTGRES_PORT')} "
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.async_pool = AsyncConnectionPool(conninfo=get_connection_str())
    yield
    await app.async_pool.close()
