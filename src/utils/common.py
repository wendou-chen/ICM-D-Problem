import requests
import time
import logging
import hashlib
from typing import Optional, Union

logger = logging.getLogger("WNBAPipeline")

class IDGenerator:
    """Generates deterministic SHA1 IDs for the warehouse."""

    @staticmethod
    def generate_id(provider: str, raw_id: Union[str, int]) -> str:
        """
        tid = sha1(provider + ":" + provider_team_id)
        """
        raw_str = f"{provider}:{raw_id}"
        return hashlib.sha1(raw_str.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_composite_id(parts: list) -> str:
        raw_str = "_".join([str(p) for p in parts])
        return hashlib.sha1(raw_str.encode('utf-8')).hexdigest()

class RequestUtils:
    """Handles HTTP requests with retries and headers mimicking a real browser."""

    # Mimic a real browser to avoid basic 403 blocks
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }

    @staticmethod
    def get(url: str, params: dict = None, headers: dict = None, retries: int = 3) -> Optional[requests.Response]:
        """Robust GET request with exponential backoff and session handling."""
        session = requests.Session()

        final_headers = RequestUtils.DEFAULT_HEADERS.copy()
        if headers:
            final_headers.update(headers)

        for i in range(retries):
            try:
                response = session.get(url, params=params, headers=final_headers, timeout=15)

                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    logger.warning(f"403 Forbidden: {url}. Attempt {i+1}/{retries}")
                    time.sleep(2 + i) # Incremental backoff
                elif response.status_code == 429:
                    logger.warning(f"429 Too Many Requests: {url}. Sleeping 10s...")
                    time.sleep(10)
                else:
                    logger.warning(f"Request failed with status {response.status_code}: {url}")
            except Exception as e:
                logger.warning(f"Request exception: {url}. Error: {e}")
                time.sleep(2)

        logger.error(f"Failed to fetch {url} after {retries} attempts.")
        return None

    @staticmethod
    def download_file(url: str, save_path: str):
        """Downloads a file to local disk."""
        response = RequestUtils.get(url)
        if response:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Downloaded {url} to {save_path}")
            return True
        return False
