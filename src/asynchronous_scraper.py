import asyncio
import base64
import os
import time
from io import BytesIO
from urllib.parse import urlparse, unquote

import aiohttp
from PIL import Image
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm as async_tqdm

BASE_DIR = "downloaded_images"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}
MAX_WORKERS = 10


async def download_and_convert(session, url, output_path, semaphore):
    async with semaphore:
        if url.startswith("data:image"):
            # Handle base64 encoded images
            image_format = url.split(";")[0].split("/")[-1]
            image_b64 = url.split(",")[1]
            image_data = base64.b64decode(image_b64)

            with open(output_path, "wb") as f:
                f.write(image_data)
        else:

            async with session.get(url) as response:
                if response.status != 200 or "image" not in response.headers.get(
                    "Content-Type", ""
                ):
                    print(f"Skipping non-image URL: {url}")
                    return
                image_data = await response.read()

            image = Image.open(BytesIO(image_data))
            image.save(output_path, "PNG")


async def get_soup(session, url):
    async with session.get(url) as response:
        content = await response.text()
    return BeautifulSoup(content, "html.parser")


async def scrape_one(session, img_tag, semaphore):
    img_url = img_tag.get("src")
    if img_url:
        parsed_url = urlparse(img_url)
        base_file_name = os.path.basename(unquote(parsed_url.path))

        base_file_name_without_ext = os.path.splitext(base_file_name)[0][:25]
        file_name = os.path.join(BASE_DIR, f"{base_file_name_without_ext}.png")

        semaphore = asyncio.Semaphore(MAX_WORKERS) # for rate limiting

        async with semaphore:
            await download_and_convert(session, img_url, file_name, semaphore)

    return img_tag


async def scrape_images(search_query):
    unsplash_url = f"https://unsplash.com/s/photos/{search_query}"

    # Create the semaphore here
    semaphore = asyncio.Semaphore(MAX_WORKERS)

    async with aiohttp.ClientSession() as session:
        soup = await get_soup(session, unsplash_url)

        # Find all img tags
        img_tags = soup.find_all("img")

        print(
            f"Found {len(img_tags)} images to download..."
        )

        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR)

        # Pass the semaphore to each task
        tasks = [scrape_one(session, tag, semaphore) for tag in img_tags]

        res = []
        for coro in async_tqdm.as_completed(
                tasks, total=len(img_tags), desc="Downloading"
        ):
            # Collect the result from the coroutine
            result = await coro
            res.append(result)

    return len(res)


def main():
    t0 = time.time()
    count = asyncio.run(scrape_images("dog"))
    elapsed = time.time() - t0
    # msg = '\n{} dog pics downloaded in {:.2f}s'
    print(f"\n{count} dog pics downloaded in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
