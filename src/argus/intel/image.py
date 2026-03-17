"""Image intelligence -- perceptual hashing, EXIF extraction."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig

logger = logging.getLogger(__name__)


class ImageIntelModule:
    """Analyze images for OSINT signals (hashes, EXIF metadata)."""

    def __init__(self, session: aiohttp.ClientSession, config: ArgusConfig) -> None:
        self.session = session
        self.config = config

    async def investigate(self, image_url: str) -> dict[str, Any]:
        """Download an image and extract perceptual hash and EXIF data.

        Returns a dict with keys: url, perceptual_hash, exif, error.
        """
        result: dict[str, Any] = {
            "url": image_url,
            "perceptual_hash": None,
            "exif": {},
            "error": None,
        }

        try:
            image_bytes = await self._download_image(image_url)
        except Exception as exc:
            result["error"] = f"Download failed: {exc}"
            return result

        # Compute perceptual hash
        try:
            import imagehash
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            result["perceptual_hash"] = str(imagehash.phash(img))
        except ImportError:
            logger.warning("imagehash/Pillow not installed -- skipping perceptual hash")
        except Exception as exc:
            logger.warning("Perceptual hash failed: %s", exc)

        # Extract EXIF data
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            img = Image.open(io.BytesIO(image_bytes))
            exif_data = img.getexif()
            if exif_data:
                exif_dict: dict[str, Any] = {}
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    # Convert non-serializable values to strings
                    try:
                        if isinstance(value, bytes):
                            value = value.hex()
                        exif_dict[tag_name] = value
                    except Exception:
                        exif_dict[tag_name] = str(value)
                result["exif"] = exif_dict
        except ImportError:
            logger.warning("Pillow not installed -- skipping EXIF extraction")
        except Exception as exc:
            logger.warning("EXIF extraction failed: %s", exc)

        return result

    async def _download_image(self, url: str) -> bytes:
        """Download image bytes from a URL."""
        import aiohttp

        async with self.session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            resp.raise_for_status()
            return await resp.read()
