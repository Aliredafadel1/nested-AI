from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from modules.housing.models import Listing, ListingPhoto, ListingVerification, SavedListing, Neighborhood
from modules.housing.schemas import ListingFilters


class HousingRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_listings(self, filters: ListingFilters) -> list[Listing]:
        query = (
            select(Listing)
            .options(selectinload(Listing.photos), selectinload(Listing.verification))
            .where(Listing.status == filters.status)
        )
        if filters.neighbourhood_id:
            query = query.where(Listing.neighbourhood_id == filters.neighbourhood_id)
        if filters.min_price:
            query = query.where(Listing.price >= filters.min_price)
        if filters.max_price:
            query = query.where(Listing.price <= filters.max_price)
        if filters.bedrooms:
            query = query.where(Listing.bedrooms == filters.bedrooms)
        if filters.neighbourhood:
            query = query.join(Listing.neighborhood).where(
                Neighborhood.name.ilike(f"%{filters.neighbourhood}%")
            )
        query = query.offset(filters.skip).limit(filters.limit)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, listing_id: int) -> Listing | None:
        result = await self._db.execute(
            select(Listing)
            .options(selectinload(Listing.photos), selectinload(Listing.verification))
            .where(Listing.id == listing_id)
        )
        return result.scalar_one_or_none()

    async def create(self, landlord_id: int, data: dict) -> Listing:
        listing = Listing(landlord_id=landlord_id, **data)
        self._db.add(listing)
        await self._db.flush()
        verification = ListingVerification(listing_id=listing.id)
        self._db.add(verification)
        await self._db.flush()
        # Reload with eager-loaded relationships so serialization works
        return await self.get_by_id(listing.id)

    async def update(self, listing: Listing, data: dict) -> Listing:
        for key, value in data.items():
            if value is not None:
                setattr(listing, key, value)
        await self._db.flush()
        # Reload with eager-loaded relationships
        return await self.get_by_id(listing.id)

    async def soft_delete(self, listing: Listing) -> None:
        listing.status = "inactive"
        await self._db.flush()

    async def add_photo(self, listing_id: int, minio_key: str, is_primary: bool = False) -> ListingPhoto:
        photo = ListingPhoto(listing_id=listing_id, minio_key=minio_key, is_primary=is_primary)
        self._db.add(photo)
        await self._db.flush()
        return photo

    async def count_photos(self, listing_id: int) -> int:
        from sqlalchemy import func, select
        result = await self._db.execute(
            select(func.count()).where(ListingPhoto.listing_id == listing_id)
        )
        return result.scalar_one()

    async def save_listing(self, user_id: int, listing_id: int) -> SavedListing:
        from sqlalchemy import text
        # Use upsert to handle duplicate saves gracefully
        await self._db.execute(
            text(
                "INSERT INTO saved_listings (user_id, listing_id) "
                "VALUES (:uid, :lid) ON CONFLICT DO NOTHING"
            ),
            {"uid": user_id, "lid": listing_id},
        )
        await self._db.flush()

    async def unsave_listing(self, user_id: int, listing_id: int) -> None:
        result = await self._db.execute(
            select(SavedListing).where(
                and_(SavedListing.user_id == user_id, SavedListing.listing_id == listing_id)
            )
        )
        saved = result.scalar_one_or_none()
        if saved:
            await self._db.delete(saved)
            await self._db.flush()

    async def get_saved_listings(self, user_id: int) -> list[Listing]:
        result = await self._db.execute(
            select(Listing)
            .options(selectinload(Listing.photos), selectinload(Listing.verification))
            .join(SavedListing, Listing.id == SavedListing.listing_id)
            .where(SavedListing.user_id == user_id)
        )
        return list(result.scalars().all())

    async def update_embedding(self, listing_id: int, vector: list[float]) -> None:
        from sqlalchemy import text
        await self._db.execute(
            text("UPDATE listings SET embedding = :vec WHERE id = :id"),
            {"vec": str(vector), "id": listing_id},
        )
        await self._db.flush()

    async def semantic_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_price: int | None = None,
        max_price: int | None = None,
        neighbourhood_id: int | None = None,
    ) -> list[Listing]:
        from sqlalchemy import text
        filters = ["l.status = 'active'", "l.embedding IS NOT NULL"]
        params: dict = {"vec": str(query_embedding), "limit": limit}
        if min_price is not None:
            filters.append("l.price >= :min_price")
            params["min_price"] = min_price
        if max_price is not None:
            filters.append("l.price <= :max_price")
            params["max_price"] = max_price
        if neighbourhood_id is not None:
            filters.append("l.neighbourhood_id = :neighbourhood_id")
            params["neighbourhood_id"] = neighbourhood_id

        where_clause = " AND ".join(filters)
        sql = text(
            f"""
            SELECT l.id FROM listings l
            WHERE {where_clause}
            ORDER BY l.embedding <=> :vec::vector
            LIMIT :limit
            """
        )
        result = await self._db.execute(sql, params)
        ids = [row[0] for row in result.fetchall()]
        if not ids:
            return []
        listings = []
        for listing_id in ids:
            listing = await self.get_by_id(listing_id)
            if listing:
                listings.append(listing)
        return listings

    async def get_neighbourhood_stats(self, neighbourhood_id: int) -> dict:
        from sqlalchemy import text
        result = await self._db.execute(
            text(
                """
                SELECT AVG(price)::float, STDDEV(price)::float
                FROM listings
                WHERE neighbourhood_id = :nid AND status = 'active'
                """
            ),
            {"nid": neighbourhood_id},
        )
        row = result.fetchone()
        return {
            "median": row[0] or 0.0,
            "stddev": row[1] or 1.0,
        }

    async def get_landlord_listing_count(self, landlord_id: int) -> int:
        from sqlalchemy import text
        result = await self._db.execute(
            text("SELECT COUNT(*) FROM listings WHERE landlord_id = :lid"),
            {"lid": landlord_id},
        )
        return result.scalar_one() or 0

    async def get_listing_photo_phashes(self, listing_id: int) -> list[str]:
        from sqlalchemy import text
        result = await self._db.execute(
            text(
                "SELECT phash FROM listing_photos "
                "WHERE listing_id = :lid AND phash IS NOT NULL"
            ),
            {"lid": listing_id},
        )
        return [row[0] for row in result.fetchall()]

    async def get_saved_count(self, listing_id: int) -> int:
        from sqlalchemy import text
        result = await self._db.execute(
            text("SELECT COUNT(*) FROM saved_listings WHERE listing_id = :lid"),
            {"lid": listing_id},
        )
        return result.scalar_one() or 0

    async def get_ip_listing_count(self, ip_address: str, hours: int = 24) -> int:
        """Count how many listings were created from this IP in the last N hours."""
        from sqlalchemy import text
        result = await self._db.execute(
            text(
                "SELECT COUNT(*) FROM listings "
                "WHERE ip_address = :ip "
                "AND created_at >= NOW() - ((:hours || ' hours')::interval)"
            ),
            {"ip": ip_address, "hours": str(hours)},
        )
        return result.scalar_one() or 0

    async def get_similar_listing_embeddings(
        self, listing_id: int, limit: int = 5
    ) -> list[dict]:
        """Return the closest listings by embedding cosine distance (excludes self)."""
        from sqlalchemy import text
        result = await self._db.execute(
            text(
                """
                SELECT id, (embedding <=> (
                    SELECT embedding FROM listings WHERE id = :lid
                )) AS distance
                FROM listings
                WHERE id != :lid
                  AND status = 'active'
                  AND embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT :limit
                """
            ),
            {"lid": listing_id, "limit": limit},
        )
        return [{"listing_id": row[0], "distance": float(row[1])} for row in result.fetchall()]
