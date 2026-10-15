from database.connection import Base, engine
from database import models  # noqa: F401
from workflows import models as workflow_models  # noqa: F401
from economy import models as economy_models  # noqa: F401


def initialize_database():
    Base.metadata.create_all(
        bind=engine
    )


if __name__ == "__main__":
    initialize_database()
    print("SAGE DATABASE INITIALIZED")