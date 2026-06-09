from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import require_landlord, require_student_role
from modules.housing.schemas import ListingCreate, ListingFilters, ListingOut, ListingUpdate
from modules.housing.service import HousingService

router = APIRouter(prefix="/listings", tags=["listings"])


def _svc(db: AsyncSession = Depends(get_db)) -> HousingService:
    return HousingService(db)


@router.get("", response_model=list[ListingOut])
async def list_listings(
    neighbourhood: str | None = Query(None),
    neighbourhood_id: int | None = Query(None),
    min_price: int | None = Query(None),
    max_price: int | None = Query(None),
    bedrooms: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    svc: HousingService = Depends(_svc),
):
    filters = ListingFilters(
        neighbourhood=neighbourhood,
        neighbourhood_id=neighbourhood_id,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        skip=skip,
        limit=limit,
    )
    return await svc.get_listings(filters)


@router.get("/saved", response_model=list[ListingOut])
async def get_saved(
    current_user: dict = Depends(require_student_role),
    svc: HousingService = Depends(_svc),
):
    return await svc.get_saved_listings(int(current_user["sub"]))


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: int, svc: HousingService = Depends(_svc)):
    return await svc.get_listing(listing_id)


@router.post("", response_model=ListingOut, status_code=201)
async def create_listing(
    request: Request,
    data: ListingCreate,
    current_user: dict = Depends(require_landlord),
    svc: HousingService = Depends(_svc),
):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    return await svc.create_listing(int(current_user["sub"]), data, ip_address=client_ip)


@router.put("/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: int,
    data: ListingUpdate,
    current_user: dict = Depends(require_landlord),
    svc: HousingService = Depends(_svc),
):
    return await svc.update_listing(listing_id, int(current_user["sub"]), data)


@router.delete("/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: int,
    current_user: dict = Depends(require_landlord),
    svc: HousingService = Depends(_svc),
):
    await svc.delete_listing(listing_id, int(current_user["sub"]))


@router.post("/{listing_id}/photos", status_code=201)
async def upload_photo(
    listing_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_landlord),
    svc: HousingService = Depends(_svc),
):
    url = await svc.upload_photo(listing_id, int(current_user["sub"]), file)
    return {"url": url}


@router.get("/{listing_id}/stats")
async def listing_stats(
    listing_id: int,
    current_user: dict = Depends(require_landlord),
    svc: HousingService = Depends(_svc),
):
    return await svc.get_listing_stats(listing_id, int(current_user["sub"]))


@router.post("/{listing_id}/save", status_code=204)
async def save_listing(
    listing_id: int,
    current_user: dict = Depends(require_student_role),
    svc: HousingService = Depends(_svc),
):
    await svc.save_listing(int(current_user["sub"]), listing_id)


@router.delete("/{listing_id}/save", status_code=204)
async def unsave_listing(
    listing_id: int,
    current_user: dict = Depends(require_student_role),
    svc: HousingService = Depends(_svc),
):
    await svc.unsave_listing(int(current_user["sub"]), listing_id)
