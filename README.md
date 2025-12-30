# Råsa Pantern

Managed by UV

## Running standalone

1. Fill in example.env file and rename to .env

2. Set up database with:

    ```sh
    export DB_FILE=./db.sqlite
    uv run db_handler.py
    ```

3. Run with `uv run main.py`

## Running with podman/docker and sqlite

1. Set up database to be volume mounted:

    ```sh
    mkdir ./db
    export DB_FILE=./db/db.sqlite
    uv run db_handler.py
    chmod -R g+rw ./db
    ```

2. Bind mount db.sqlite into a reasonable directory (like /app/db/db.sqlite).

3. Run with evironment variables DB_FILE set to the binded location,
   and TOKEN set to your discord token.

example:

```sh
podman run -it --userns=keep-id\
           -e DB_FILE="/app/db/db.sqlite" \
           -e TOKEN="<your token here>" \
           -v ./db:/app/db\
           rasa-pantern
```

you can also use `command="uv run -m db_handling.handler` to create and
initialize the database, as long as your group has permissions to write to the
mounted database folder

The reason we mount a folder and not just the file is because sqlite needs to
create and write to a few additional files apart from the database itself, and
thus we need a folder with write access.

## Running with podman/docker and postgres

**This is the recomended option.**

1. Open the compose file and uncomment the setup command line `command: uv run
   -m db_handling.handler`

2. Fill in all environment variables in the compose file

3. Start the services with `podman compose up`

4. Remove the command line from the compose file

5. Start the proper Bot service with `podman compose up -d`
