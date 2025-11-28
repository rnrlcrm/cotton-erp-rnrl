"""
Root conftest for all backend tests

Registers SQLite type compilers for PostgreSQL types.
This MUST be at the root level so it's loaded before any test collection.
"""

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID, JSONB

@compiles(UUID, 'sqlite')
def compile_uuid_sqlite(type_, compiler, **kw):
    """Compile PostgreSQL UUID to TEXT for SQLite"""
    return "TEXT"

@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    """Compile PostgreSQL JSONB to JSON for SQLite"""
    return "JSON"
