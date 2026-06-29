from core.db.models import Base, LLMProviderConfig, RepositoryConfig, SystemMeta


def test_orm_tables_registered():
    names = set(Base.metadata.tables.keys())
    assert "repository_config" in names
    assert "llm_provider_config" in names
    assert "system_meta" in names


def test_llm_provider_config_priority_column():
    col = LLMProviderConfig.__table__.c.priority
    assert col is not None


def test_system_meta_column_defaults():
    col = SystemMeta.__table__.c.setup_completed
    assert col.default is not None or col.server_default is not None
