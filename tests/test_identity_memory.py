from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from identity import memory


def test_profile_memory_is_user_scoped_and_editable(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'memory.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(memory, "SessionLocal", session_factory)

    created = memory.add_memory(
        profile_id="profile-1",
        memory_type="skill",
        content="Video editing",
        confidence=0.8,
        confirmed=True,
    )

    assert created["profile_id"] == "profile-1"
    assert created["memory_type"] == "skill"
    assert created["confirmed"] is True

    assert memory.list_memory("profile-2") == []

    updated = memory.update_memory(
        created["id"],
        "profile-1",
        confidence=0.95,
        memory_type="skill_evidence",
    )

    assert updated is not None
    assert updated["confidence"] == 0.95
    assert updated["memory_type"] == "skill_evidence"

    assert memory.delete_memory(created["id"], "profile-2") is False
    assert memory.delete_memory(created["id"], "profile-1") is True
    assert memory.list_memory("profile-1") == []
