import asyncio
import base64
import os
import time
from io import BytesIO
from urllib.parse import urlparse, unquote

import aiohttp
from PIL import Image
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_DIR = "downloaded_images"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}
MAX_WORKERS = 10


async def download_and_convert(session, url, output_path):
    if url.startswith("data:image"):
        # Handle base64 encoded images
        image_format = url.split(";")[0].split("/")[-1]
        image_b64 = url.split(",")[1]
        image_data = base64.b64decode(image_b64)

        with open(output_path, "wb") as f:
            f.write(image_data)
    else:
        try:
            async with session.get(url) as response:
                response.raise_for_status()  # Raises an error if the HTTP request returned an unsuccessful status code
                if "image" not in response.headers.get("Content-Type", ""):
                    raise ValueError("URL is not an image")

                image_data = await response.read()

            image = Image.open(BytesIO(image_data))
            image.save(output_path, "PNG")
        except (aiohttp.ClientError, aiohttp.ServerTimeoutError, ValueError) as e:
            print(f"Error downloading {url}. Reason: {str(e)}")


async def get_soup(session, url):
    async with session.get(url) as response:
        content = await response.text()
    return BeautifulSoup(content, "html.parser")


async def scrape_one(session, img_tag):
    img_url = img_tag.get("src")
    if img_url:
        parsed_url = urlparse(img_url)
        base_file_name = os.path.basename(unquote(parsed_url.path))

        base_file_name_without_ext = os.path.splitext(base_file_name)[0][:25]
        file_name = os.path.join(BASE_DIR, f"{base_file_name_without_ext}.png")

        await download_and_convert(session, img_url, file_name)

    return img_tag


async def safe_scrape_one(session, tag, progress_bar=None):
    """
    Wraps around scrape_one, catches exceptions from single image download.

    :param session:
    :param tag:
    :param progress_bar:
    :return:
    """
    try:
        result = await scrape_one(session, tag)
        if progress_bar:
            progress_bar.update(1)
        return result
    except Exception as e:
        if progress_bar:
            progress_bar.update(1)
        print(f"Error processing image: {e}")
        return None


async def scrape_images(search_query):
    unsplash_url = f"https://unsplash.com/s/photos/{search_query}"

    async with aiohttp.ClientSession() as session:
        soup = await get_soup(session, unsplash_url)

        # Find all img tags
        img_tags = soup.find_all("img")

        print(f"Found {len(img_tags)} images to download...")

        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR)

        with tqdm(total=len(img_tags), desc="Downloading") as progress_bar:
            tasks = [safe_scrape_one(session, tag, progress_bar) for tag in img_tags]
            res = await asyncio.gather(*tasks, return_exceptions=True)

    return len([r for r in res if res])


async def main():
    t0 = time.time()
    count = await scrape_images("dog")
    elapsed = time.time() - t0
    print(f"\n{count} dog pics downloaded in {elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
