import uuid
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.storage import upload_file, Bucket, get_public_url
from modules.housing.repository import HousingRepository
from modules.housing.schemas import ListingCreate, ListingUpdate, ListingFilters
from modules.housing.models import Listing

MAX_PHOTOS_PER_LISTING = 20


class HousingService:
    def __init__(self, db: AsyncSession):
        self._repo = HousingRepository(db)

    async def get_listings(self, filters: ListingFilters) -> list[Listing]:
        return await self._repo.get_listings(filters)

    async def get_listing(self, listing_id: int) -> Listing:
        listing = await self._repo.get_by_id(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found.")
        return listing

    async def create_listing(
        self, landlord_id: int, data: ListingCreate, ip_address: str | None = None
    ) -> Listing:
        payload = data.model_dump()
        if ip_address:
            payload["ip_address"] = ip_address
        listing = await self._repo.create(landlord_id, payload)
        from modules.housing.tasks import embed_listing
        embed_listing.delay(listing.id)
        from modules.fraud.tasks import run_fraud_check
        run_fraud_check.delay(listing.id)
        return listing

    async def update_listing(self, listing_id: int, landlord_id: int, data: ListingUpdate) -> Listing:
        listing = await self._get_own_listing(listing_id, landlord_id)
        updated = await self._repo.update(listing, data.model_dump(exclude_none=True))
        from modules.housing.tasks import embed_listing
        embed_listing.delay(listing_id)
        return updated

    async def delete_listing(self, listing_id: int, landlord_id: int) -> None:
        listing = await self._get_own_listing(listing_id, landlord_id)
        await self._repo.soft_delete(listing)

    async def upload_photo(self, listing_id: int, landlord_id: int, file: UploadFile) -> str:
        listing = await self._get_own_listing(listing_id, landlord_id)
        count = await self._repo.count_photos(listing_id)
        if count >= MAX_PHOTOS_PER_LISTING:
            raise HTTPException(status_code=400, detail=f"Max {MAX_PHOTOS_PER_LISTING} photos per listing.")

        object_name = f"{listing_id}/{uuid.uuid4()}"
        await upload_file(file, Bucket.LISTING_PHOTOS, object_name, owner_id=landlord_id)
        is_primary = count == 0
        await self._repo.add_photo(listing_id, object_name, is_primary)
        return get_public_url(Bucket.LISTING_PHOTOS, object_name)

    async def save_listing(self, user_id: int, listing_id: int) -> None:
        listing = await self._repo.get_by_id(listing_id)
        if not listing or listing.status != "active":
            raise HTTPException(status_code=404, detail="Listing not found.")
        await self._repo.save_listing(user_id, listing_id)

    async def unsave_listing(self, user_id: int, listing_id: int) -> None:
        await self._repo.unsave_listing(user_id, listing_id)

    async def get_saved_listings(self, user_id: int) -> list[Listing]:
        return await self._repo.get_saved_listings(user_id)

    async def get_listing_stats(self, listing_id: int, landlord_id: int) -> dict:
        await self._get_own_listing(listing_id, landlord_id)
        count = await self._repo.get_saved_count(listing_id)
        return {"listing_id": listing_id, "saved_count": count}

    async def semantic_search(
        self,
        query_embedding: list[float],
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[Listing]:
        f = filters or {}
        return await self._repo.semantic_search(
            query_embedding=query_embedding,
            limit=limit,
            min_price=f.get("min_price"),
            max_price=f.get("max_price"),
            neighbourhood_id=f.get("neighbourhood_id"),
        )

    async def get_neighbourhood_stats(self, neighbourhood_id: int) -> dict:
        return await self._repo.get_neighbourhood_stats(neighbourhood_id)

    async def get_landlord_listing_count(self, landlord_id: int) -> int:
        return await self._repo.get_landlord_listing_count(landlord_id)

    async def get_listing_photo_phashes(self, listing_id: int) -> list[str]:
        return await self._repo.get_listing_photo_phashes(listing_id)

    async def get_ip_listing_count(self, ip_address: str, hours: int = 24) -> int:
        return await self._repo.get_ip_listing_count(ip_address, hours)

    async def get_similar_listing_embeddings(self, listing_id: int, limit: int = 5) -> list[dict]:
        return await self._repo.get_similar_listing_embeddings(listing_id, limit)

    async def _get_own_listing(self, listing_id: int, landlord_id: int) -> Listing:
        listing = await self._repo.get_by_id(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found.")
        if listing.landlord_id != landlord_id:
            raise HTTPException(status_code=403, detail="You do not own this listing.")
        return listing
