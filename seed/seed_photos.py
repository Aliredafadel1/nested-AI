"""
Seed real apartment photos for all active listings.
Downloads from Unsplash (free, no key needed) and uploads to MinIO.
Run inside the API container:
  docker exec docker-api-1 python /app/seed/seed_photos.py
"""
import io
import ssl
import time
import urllib.error
import urllib.request
import uuid

import psycopg2
from minio import Minio

# ── Config ────────────────────────────────────────────────────────────────────
MINIO_ENDPOINT  = "minio:9000"
MINIO_USER      = "nestai"
MINIO_PASSWORD  = "nestai_secret"
BUCKET          = "listing-photos"
DB_DSN          = "postgresql://nestai:nestai@db/nestai"

# ── Curated Unsplash photo pool ───────────────────────────────────────────────
# Free-to-use Unsplash photos of apartments / interiors (no API key required)
# Format: https://images.unsplash.com/{id}?auto=format&fit=crop&w=800&q=80
UNSPLASH_BASE = "https://images.unsplash.com/{id}?auto=format&fit=crop&w=800&q=80"

PHOTOS = {
    # Studios / compact
    "studio": [
        "photo-1502672260266-1c1ef2d93688",  # cozy bedroom
        "photo-1560185007-c5ca9d2c014d",     # minimal white bedroom
        "photo-1555041469-a6f5ea2e7b15",     # modern sofa & living area
        "photo-1484154218962-a197022b5858",  # bright studio
        "photo-1574362848149-11496d93a7c7",  # compact apartment
        "photo-1558618047-3c8c9b73f3c1",     # modern studio kitchen
        "photo-1519710164239-da123dc03ef4",  # studio living space
        "photo-1493809842364-78817add7ffb",  # studio interior
    ],
    # 1-bedroom
    "1br": [
        "photo-1524758631624-e2822e304c36",  # living room plants
        "photo-1513694203232-719a280e022f",  # bright living room
        "photo-1505691938895-1758d7feb511",  # apartment hallway
        "photo-1556909211-36987daf7b4d",     # 1BR living room
        "photo-1565538810643-b5bdb714032a",  # apartment kitchen
        "photo-1567767292278-a4f21aa2d36e",  # bedroom with large window
        "photo-1600607687920-4e2a09cf159d",  # modern 1BR
        "photo-1600566753086-00f18fb6b3ea",  # nice 1BR interior
    ],
    # 2-bedroom
    "2br": [
        "photo-1600607687939-ce8a6c25118c",  # spacious living room
        "photo-1600585154340-be6161a56a0c",  # 2BR apartment
        "photo-1600596542815-ffad4c1539a9",  # bright apartment
        "photo-1600566752355-35792bedcfea",  # 2BR kitchen
        "photo-1560184897-ae75f418493e",     # large apartment living area
        "photo-1568605114967-8130f3a36994",  # apartment exterior view
        "photo-1583847268964-b28dc8f51f92",  # 2BR interior
        "photo-1609766857663-a4c8a04de3de",  # modern apartment
    ],
    # 3-bedroom / large
    "3br": [
        "photo-1618221195710-dd6b41faaea6",  # large living room
        "photo-1600210491892-03d54730d73e",  # spacious apartment
        "photo-1600047509807-ba8f99d2cdde",  # luxury apartment
        "photo-1600566753190-17f0baa2a6c3",  # 3BR interior
        "photo-1600585154526-990dced4db0d",  # luxury kitchen
        "photo-1600047509358-9dc75507daeb",  # penthouse style
        "photo-1573652000953-49e784cce8dc",  # large living space
        "photo-1560448075-bb485b067938",     # modern large apartment
    ],
    # Exterior / building shots (used as 2nd/3rd photo)
    "exterior": [
        "photo-1580587771525-78b9dba3b914",  # apartment building exterior
        "photo-1545324418-cc1a3fa10c00",     # Beirut-style balcony building
        "photo-1486325212027-8081e485255e",  # mediterranean building
        "photo-1523217582562-09d0def993a6",  # white building with balconies
        "photo-1477959858617-67f85cf4f1df",  # city apartment buildings
        "photo-1584271854089-9bb3e5168e8d",  # modern residential building
    ],
}

# Map bedroom count → photo pools to cycle through
def get_photo_pool(bedrooms: int) -> list:
    if bedrooms == 1:
        pool = PHOTOS["studio"] + PHOTOS["1br"]
    elif bedrooms == 2:
        pool = PHOTOS["1br"] + PHOTOS["2br"]
    else:
        pool = PHOTOS["2br"] + PHOTOS["3br"]
    return pool

def photos_per_listing(bedrooms: int) -> int:
    return 3 if bedrooms >= 2 else 2


def download_photo(photo_id: str) -> bytes | None:
    url = UNSPLASH_BASE.format(id=photo_id)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NestAI-seeder/1.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = resp.read()
            if len(data) < 5000:  # suspiciously small — probably an error page
                return None
            return data
    except Exception as e:
        print(f"  [WARN] Failed to download {photo_id}: {e}")
        return None


def upload_to_minio(client: Minio, listing_id: int, data: bytes, is_primary: bool) -> str:
    key = f"{listing_id}/{uuid.uuid4()}"
    client.put_object(
        bucket_name=BUCKET,
        object_name=key,
        data=io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg",
    )
    return key


def main():
    minio = Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASSWORD, secure=False)

    # Ensure bucket exists
    if not minio.bucket_exists(BUCKET):
        minio.make_bucket(BUCKET)
        print(f"Created bucket: {BUCKET}")

    # Set bucket policy to public-read so photos are viewable without presigned URLs
    import json
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{BUCKET}/*"],
        }]
    }
    minio.set_bucket_policy(BUCKET, json.dumps(policy))

    conn = psycopg2.connect(DB_DSN)
    cur  = conn.cursor()

    # Only seed listings that have no photos yet
    cur.execute("""
        SELECT l.id, l.bedrooms
        FROM listings l
        LEFT JOIN listing_photos lp ON lp.listing_id = l.id
        WHERE l.status = 'active' AND lp.id IS NULL
        ORDER BY l.id
    """)
    listings = cur.fetchall()
    print(f"Listings without photos: {len(listings)}")

    pool_index: dict[str, int] = {}  # track rotation per pool key

    for listing_id, bedrooms in listings:
        pool      = get_photo_pool(bedrooms)
        n_photos  = photos_per_listing(bedrooms)
        pool_key  = f"{'studio' if bedrooms < 2 else str(bedrooms)+'br'}"

        print(f"\nListing {listing_id} ({bedrooms}BR) — uploading {n_photos} photo(s)...")

        # Always add an exterior as the last photo for 2BR+
        interior_pool = pool
        exterior_pool = PHOTOS["exterior"]

        uploaded = 0
        photo_idx = pool_index.get(pool_key, 0)

        for i in range(n_photos):
            if i == n_photos - 1 and bedrooms >= 2:
                # Last photo = exterior
                ext_idx = pool_index.get("exterior", 0)
                photo_id = exterior_pool[ext_idx % len(exterior_pool)]
                pool_index["exterior"] = ext_idx + 1
            else:
                photo_id = interior_pool[photo_idx % len(interior_pool)]
                photo_idx += 1

            data = download_photo(photo_id)
            if not data:
                print(f"  Skipping photo {photo_id} (download failed)")
                continue

            key = upload_to_minio(minio, listing_id, data, is_primary=(i == 0))
            is_primary = (i == 0)
            cur.execute(
                "INSERT INTO listing_photos (listing_id, minio_key, is_primary) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (listing_id, key, is_primary),
            )
            conn.commit()
            uploaded += 1
            print(f"  [{i+1}/{n_photos}] Uploaded {photo_id[:30]}... → {key}")
            time.sleep(0.3)  # be polite to Unsplash

        pool_index[pool_key] = photo_idx

    cur.close()
    conn.close()
    print("\nDone. All listings seeded with photos.")


if __name__ == "__main__":
    main()
