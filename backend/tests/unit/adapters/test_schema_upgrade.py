import pytest
from sqlalchemy.engine import make_url

from adapters.out.sqlalchemy.schema_upgrade import (
    SchemaUpgradeRefused,
    direct_asyncpg_url,
)


def test_direct_asyncpg_url_turns_a_neon_connection_string_into_an_asyncpg_url_with_ssl_and_no_channel_binding() -> (  # noqa: E501
    None
):
    raw = (
        "postgres://weles_owner:s3cret@ep-cool-forest-123456.us-east-2.aws.neon.tech"
        + "/weles?sslmode=require&channel_binding=require"
    )

    result = direct_asyncpg_url(raw)

    assert result == make_url(
        "postgresql+asyncpg://weles_owner:s3cret@"
        + "ep-cool-forest-123456.us-east-2.aws.neon.tech/weles?ssl=require"
    )


def test_direct_asyncpg_url_refuses_a_pooler_host_and_points_at_the_direct_connection_string() -> (  # noqa: E501
    None
):
    raw = (
        "postgres://weles_owner:s3cret@ep-cool-forest-123456-pooler.us-east-2"
        + ".aws.neon.tech/weles?sslmode=require&channel_binding=require"
    )

    with pytest.raises(SchemaUpgradeRefused, match="direct connection string"):
        _ = direct_asyncpg_url(raw)


def test_direct_asyncpg_url_refuses_a_non_postgres_scheme() -> None:
    with pytest.raises(SchemaUpgradeRefused):
        _ = direct_asyncpg_url("mysql://weles_owner:s3cret@example.com/weles")
