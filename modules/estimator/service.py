from __future__ import annotations

import logging

import httpx
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from modules.area_intel.service import AreaIntelService
from modules.estimator.repository import EstimatorRepository
from core.features import electricity_reliability, livability_score, student_score
from modules.estimator.schemas import AreaScores, CostBreakdown, EstimateOut, EstimateRequest, SimulateOut, SimulateRequest

logger = logging.getLogger(__name__)

WATER_FIXED    = 15   # USD/month — Lebanon tanker average for one person
INTERNET_FIXED = 30   # USD/month — mid-tier ISP plan


class EstimatorService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self._db       = db
        self._repo     = EstimatorRepository(db)
        self._area_svc = AreaIntelService(db, redis)

    async def calculate(self, user_id: int, req: EstimateRequest) -> EstimateOut:
        neighbourhood = await self._area_svc.get_by_id(req.neighbourhood_id)
        generator = neighbourhood.generator_cost or 40
        transport = (neighbourhood.transport or 3) * 10  # score 1–5 → 10–50 USD

        commute_minutes = await self._get_commute(
            neighbourhood_id=req.neighbourhood_id,
            university_id=req.university_id,
        )

        total = req.rent + generator + WATER_FIXED + INTERNET_FIXED + transport
        await self._repo.save(
            user_id=user_id,
            rent=req.rent,
            generator=generator,
            water=WATER_FIXED,
            internet=INTERNET_FIXED,
            transport=transport,
            total_monthly=total,
            university_id=req.university_id,
        )
        return EstimateOut(
            rent=req.rent,
            generator=generator,
            water=WATER_FIXED,
            internet=INTERNET_FIXED,
            transport=transport,
            total_monthly=total,
            commute_minutes=commute_minutes,
        )

    async def simulate(self, user_id: int, req: SimulateRequest) -> SimulateOut:
        area = await self._area_svc.get_by_id(req.neighbourhood_id)

        generator = area.generator_cost or 40
        transport_cost = (area.transport or 3) * 10
        total = req.budget + generator + WATER_FIXED + INTERNET_FIXED + transport_cost

        commute_minutes = await self._get_commute(req.neighbourhood_id, req.university_id)

        elec_hours = float(area.electricity or 12)
        gen_hours = 24.0 - elec_hours
        elec_label = f"{elec_hours:.0f}h EDL · {gen_hours:.0f}h generator"

        elec_rel = electricity_reliability(area.electricity)
        liv = livability_score(area.electricity, area.internet, area.safety, area.transport)
        stu = student_score(area.student_vibe, area.transport, area.safety, area.internet)

        # Budget feasibility: compare total monthly vs 1.5× budget
        if total <= req.budget * 1.15:
            feasibility = "comfortable"
        elif total <= req.budget * 1.40:
            feasibility = "tight"
        else:
            feasibility = "over budget"

        # Fit score: student_score weighted 60%, livability 40%
        fit = round(stu * 0.6 + liv * 0.4, 3)

        return SimulateOut(
            neighbourhood_name=area.name,
            neighbourhood_name_ar=area.name_ar,
            area_scores=AreaScores(
                electricity_hours=area.electricity,
                electricity_reliability=elec_rel,
                generator_cost=area.generator_cost,
                internet=area.internet,
                transport=area.transport,
                safety=area.safety,
                student_vibe=area.student_vibe,
                livability_score=liv,
                student_score=stu,
            ),
            cost_breakdown=CostBreakdown(
                rent=req.budget,
                generator=generator,
                water=WATER_FIXED,
                internet=INTERNET_FIXED,
                transport=transport_cost,
                total_monthly=total,
            ),
            commute_minutes=commute_minutes,
            fit_score=fit,
            electricity_label=elec_label,
            budget_feasibility=feasibility,
        )

    async def _get_commute(
        self, neighbourhood_id: int, university_id: int | None
    ) -> int | None:
        if not university_id:
            return None
        try:
            uni_row = await self._db.execute(
                text("SELECT lat, lng FROM universities WHERE id = :id"),
                {"id": university_id},
            )
            uni = uni_row.fetchone()
            if not uni:
                return None

            nbhd_row = await self._db.execute(
                text("SELECT lat, lng FROM neighborhoods WHERE id = :id"),
                {"id": neighbourhood_id},
            )
            nbhd = nbhd_row.fetchone()
            if not nbhd or nbhd.lat is None:
                return None

            osrm_url = (
                f"{settings.OSRM_URL}/route/v1/driving/"
                f"{float(nbhd.lng)},{float(nbhd.lat)};"
                f"{float(uni.lng)},{float(uni.lat)}"
                f"?overview=false"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(osrm_url)
                data = resp.json()
                duration_seconds = data["routes"][0]["duration"]
                return int(duration_seconds / 60)
        except Exception as e:
            logger.warning("estimator._get_commute | OSRM unavailable: %s", e)
            return None
