from __future__ import annotations

import importlib.util
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add repository root to sys.path to allow `import backend.*`
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from backend.db.session import Base  # noqa: E402

# Import models so that they are registered on Base.metadata for autogenerate
from backend.modules.settings.models import settings_models as _models  # noqa: F401,E402
from backend.modules.settings.organization.models import (  # noqa: F401,E402
    Organization,
    OrganizationGST,
    OrganizationBankAccount,
    OrganizationFinancialYear,
    OrganizationDocumentSeries,
)
from backend.modules.settings.commodities.models import (  # noqa: F401,E402
    Commodity,
    CommodityVariety,
    CommodityParameter,
    SystemCommodityParameter,
    PaymentTerm,
    DeliveryTerm,
    WeightmentTerm,
    PassingTerm,
    BargainType,
    TradeType,
    CommissionStructure,
)
from backend.modules.settings.commodities.hsn_models import (  # noqa: F401,E402
    HSNKnowledgeBase,
)
from backend.modules.partners.models import (  # noqa: F401,E402
    BusinessPartner,
)
from backend.modules.settings.locations.models import Location  # noqa: F401,E402
from backend.modules.trade_desk.models.requirement import Requirement  # noqa: F401,E402
from backend.modules.trade_desk.models.availability import Availability  # noqa: F401,E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _include_object(object, name, type_, reflected, compare_to):  # noqa: ANN001
    # Avoid re-generating composite unique constraints that are redundant with PK
    if type_ == "unique_constraint" and name in {"uq_role_permission", "uq_user_role"}:
        return False
    return True


def get_database_url() -> str:
    # Keep in sync with backend/db/session.py default for now
    return os.getenv(
        "DATABASE_URL",
        # ⚠️ SECURITY: Use environment variable in production
        "postgresql+psycopg://postgres:postgres@localhost:5432/cotton_dev",  # Dev fallback only
    )


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=_include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg_section = config.get_section(config.config_ini_section) or {}
    cfg_section["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=_include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
