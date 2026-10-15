from database.connection import SessionLocal
from database.repository import repository


class MemoryManager:

    def add(
        self,
        content,
        memory_type="fact",
        importance=0.5,
        confidence=1.0,
        source="conversation",
        owner_confirmed=False
    ):
        db = SessionLocal()

        try:
            return repository.add_memory(
                db=db,
                content=content,
                memory_type=memory_type,
                importance=importance,
                confidence=confidence,
                source=source
            )
        finally:
            db.close()

    def all(self):
        db = SessionLocal()

        try:
            memories = repository.get_memories(
                db,
                limit=100
            )

            return [
                {
                    "id": item.id,
                    "type": item.memory_type,
                    "content": item.content,
                    "importance": item.importance,
                    "confidence": item.confidence,
                    "source": item.source,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat()
                }
                for item in memories
            ]

        finally:
            db.close()

    def relevant(self, query, limit=5):
        memories = self.all()

        if not memories:
            return []

        words = set(
            query.lower().split()
        )

        scored = []

        for memory in memories:
            content = memory["content"].lower()

            score = sum(
                1
                for word in words
                if len(word) > 2 and word in content
            )

            score += memory.get(
                "importance",
                0
            )

            scored.append(
                (score, memory)
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            memory
            for score, memory in scored[:limit]
            if score > 0
        ]


memory = MemoryManager()
