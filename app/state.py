from database.connection import SessionLocal
from database.repository import repository


class SageState:

    def create_session(self):
        db = SessionLocal()

        try:
            return repository.create_session(db)
        finally:
            db.close()

    def get_session(self, session_id):
        db = SessionLocal()

        try:
            session = repository.get_session(
                db,
                session_id
            )

            if not session:
                return None

            messages = repository.get_messages(
                db,
                session_id,
                limit=10
            )

            messages.reverse()

            return {
                "id": session.id,
                "created_at": session.created_at.isoformat(),
                "messages": [
                    {
                        "role": message.role,
                        "content": message.content,
                        "timestamp": message.created_at.isoformat()
                    }
                    for message in messages
                ],
                "current_goal": None,
                "current_task": None,
                "active_project": None
            }

        finally:
            db.close()

    def add_message(
        self,
        session_id,
        role,
        content
    ):
        db = SessionLocal()

        try:
            repository.add_message(
                db,
                session_id,
                role,
                content
            )
        finally:
            db.close()


state = SageState()