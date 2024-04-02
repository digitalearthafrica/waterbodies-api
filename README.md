# Waterbodies API

REST API for accessing information related to waterbodies that was extracted from Earth observation data.

## Architecture

The docker compose file includes two containers
- server - includes a Python based [FastAPI](https://fastapi.tiangolo.com/) application and all dependencies needed for the waterbodies-api application
- db-postgres - includes a PostgreSQL server with the PostGIS extension


## Development Environment

Clone the repo

    git clone https://github.com/digitalearthafrica/waterbodies-api.git
    cd waterbodies-api

Create an environment file that includes env vars needed by each of the docker containers. If required edit the `.env` file to connect to alternate databases, the sample file includes all details needed to connect to the DB container specified in the docker compose file.

    cp .env.sample .env

Build the waterbodies API docker containers

    docker compose build

Start the waterbodies API

    docker compose up

The application should then be accessible on localhost:8080. A simple connection check request handler can be used to ensure the web server and database are running as expected, this can be accessed at [`http://localhost:8080/check-connection`](http://localhost:8080/check-connection)


## Developing

FastAPI automatically generates documentation for request handlers added to the application, this can be accessed from the following link.

    [`http://localhost:8080/docs`](http://localhost:8080/docs) 

When using the docker compose based development environment code within the `./server/app` folder is mounted into the server container. The compose yaml also includes the `--reload` uvicorn command like arguement which means that any change to the Python source code will automatically restart the application with updated code (this is shown in docker logs). You do not need to rebuild, or stop/start the server container during development.

Chages to the requirements.txt file will require the application to be rebuilt (eg; stop the container and run `docker compose build`)


## Database

The local `./data/db` folder is mounted into the db-postgres container as `/data`. Database dumps should be placed in this folder.

TODO: notes on restoring db dump

