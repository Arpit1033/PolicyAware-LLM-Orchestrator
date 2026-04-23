from langgraph.checkpoint.postgres import PostgresSaver
from django.conf import settings
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

def _build_db_uri():
    db = settings.DATABASES['default']
    return f"postgresql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"

_checkpointer = None

def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        # ConnectionPool gives each thread its own connection from the pool,
        # eliminating the race condition of sharing a single connection.
        pool = ConnectionPool(
            conninfo=_build_db_uri(),
            max_size=10,  # max concurrent Postgres connections for checkpointing
            kwargs={
                "autocommit": True,      # Required by PostgresSaver
                "row_factory": dict_row, # Required by PostgresSaver
            }
        )
        _checkpointer = PostgresSaver(pool)
        _checkpointer.setup()  # Creates checkpoint tables if they don't exist
    return _checkpointer
