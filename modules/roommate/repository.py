from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from modules.roommate.models import RoommateRequest
from modules.roommate.schemas import MatchOut, DimensionScores


class RoommateRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_matches(self, current_user_id: int, dim_vectors: dict) -> list[MatchOut]:
        sql = text("""
            SELECT
                sp.user_id,
                ROUND(CAST((
                    (1 - (dim_sleep       <=> CAST(:sv_sleep       AS vector)))
                  + (1 - (dim_study       <=> CAST(:sv_study       AS vector)))
                  + (1 - (dim_cleanliness <=> CAST(:sv_cleanliness AS vector)))
                  + (1 - (dim_guests      <=> CAST(:sv_guests      AS vector)))
                  + (1 - (dim_budget      <=> CAST(:sv_budget      AS vector)))
                ) / 5.0 AS numeric), 4)                                      AS score,
                ROUND(CAST(1 - (dim_sleep       <=> CAST(:sv_sleep       AS vector)) AS numeric), 4) AS sleep,
                ROUND(CAST(1 - (dim_study       <=> CAST(:sv_study       AS vector)) AS numeric), 4) AS study,
                ROUND(CAST(1 - (dim_cleanliness <=> CAST(:sv_cleanliness AS vector)) AS numeric), 4) AS cleanliness,
                ROUND(CAST(1 - (dim_guests      <=> CAST(:sv_guests      AS vector)) AS numeric), 4) AS guests,
                ROUND(CAST(1 - (dim_budget      <=> CAST(:sv_budget      AS vector)) AS numeric), 4) AS budget
            FROM student_profiles sp
            WHERE sp.user_id != :current_user_id
              AND sp.dim_sleep IS NOT NULL
            ORDER BY score DESC
            LIMIT 20
        """)

        result = await self._db.execute(sql, {
            "current_user_id": current_user_id,
            "sv_sleep":        str(dim_vectors["dim_sleep"]),
            "sv_study":        str(dim_vectors["dim_study"]),
            "sv_cleanliness":  str(dim_vectors["dim_cleanliness"]),
            "sv_guests":       str(dim_vectors["dim_guests"]),
            "sv_budget":       str(dim_vectors["dim_budget"]),
        })

        rows = result.mappings().all()
        return [
            MatchOut(
                user_id=row["user_id"],
                score=float(row["score"]),
                dimensions=DimensionScores(
                    sleep=float(row["sleep"]),
                    study=float(row["study"]),
                    cleanliness=float(row["cleanliness"]),
                    guests=float(row["guests"]),
                    budget=float(row["budget"]),
                ),
            )
            for row in rows
        ]

    async def get_caller_dim_vectors(self, user_id: int) -> dict | None:
        result = await self._db.execute(
            text("""
                SELECT dim_sleep, dim_study, dim_cleanliness, dim_guests, dim_budget
                FROM student_profiles
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        )
        row = result.one_or_none()
        if row is None or row[0] is None:
            return None
        return {
            "dim_sleep":        row[0],
            "dim_study":        row[1],
            "dim_cleanliness":  row[2],
            "dim_guests":       row[3],
            "dim_budget":       row[4],
        }

    async def target_student_exists(self, user_id: int) -> bool:
        result = await self._db.execute(
            text("SELECT 1 FROM users WHERE id = :id AND role = 'student'"),
            {"id": user_id},
        )
        return result.one_or_none() is not None

    async def create_request(
        self,
        from_user_id: int,
        to_user_id: int,
        score: float | None,
        dimensions: dict,
    ) -> RoommateRequest:
        req = RoommateRequest(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            score=score,
            dimensions=dimensions,
            status="pending",
        )
        self._db.add(req)
        await self._db.flush()
        return req
