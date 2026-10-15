from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from workflows.repository import WorkflowRepository
from workflows.models import Asset, AssetRelation, Project, Workflow, Workspace


def _db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            Project.__table__,
            Asset.__table__,
            AssetRelation.__table__,
            Workflow.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def test_workflow_graph_persists_and_is_profile_scoped():
    db = _db()
    repo = WorkflowRepository()

    workspace = repo.create_workspace(
        db,
        "profile-a",
        "OROE",
        "oroe",
        "brand",
        {"tagline": "wear your essence"},
    )
    project = repo.create_project(
        db,
        workspace,
        "OROE Launch",
        "content",
        "Launch content pipeline",
    )
    image = repo.create_asset(db, project, "Hero image", "image")
    video = repo.create_asset(
        db,
        project,
        "Hero reel",
        "video",
        parent_asset_id=image.id,
    )
    relation = repo.create_relation(
        db,
        project,
        image,
        video,
        "derived_from",
    )
    workflow = repo.create_workflow(
        db,
        project,
        "Content Launch",
        "content",
        {"stages": ["idea", "create", "publish", "analyze"]},
        "idea",
    )

    assert repo.get_workspace(db, "profile-a", workspace.id) is not None
    assert repo.get_workspace(db, "profile-b", workspace.id) is None
    assert repo.get_project(db, "profile-a", project.id) is not None
    assert repo.get_project(db, "profile-b", project.id) is None
    assert [item.id for item in repo.list_assets(db, "profile-a", project.id)] == [image.id, video.id]
    assert repo.list_relations(db, "profile-a", project.id)[0].id == relation.id
    assert repo.list_workflows(db, "profile-a", project.id)[0].id == workflow.id
    assert repo.list_projects(db, "profile-b") == []

    db.close()


def test_asset_relation_rejects_self_link():
    db = _db()
    repo = WorkflowRepository()
    workspace = repo.create_workspace(db, "profile-a", "Personal", "personal", "personal")
    project = repo.create_project(db, workspace, "Project", "general")
    asset = repo.create_asset(db, project, "Asset", "file")

    try:
        repo.create_relation(db, project, asset, asset, "references")
    except ValueError as exc:
        assert "itself" in str(exc)
    else:
        raise AssertionError("self relation should be rejected")

    db.close()
