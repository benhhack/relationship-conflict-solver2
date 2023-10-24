import os
import time
from concurrent import futures
from urllib.parse import urlparse, unquote

import httpx
from bs4 import BeautifulSoup
from tqdm import tqdm

from synchronous_scraper import get_soup, download_and_convert

BASE_DIR = "downloaded_images"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}
MAX_WORKERS = 10


async def get_soup(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return BeautifulSoup(response.text, "html.parser")


def scrape_one(img_tag):
    img_url = img_tag.get("src")
    if img_url:

        parsed_url = urlparse(img_url)
        base_file_name = os.path.basename(unquote(parsed_url.path))

        base_file_name_without_ext = os.path.splitext(base_file_name)[0][:25]
        file_name = os.path.join(BASE_DIR, f"{base_file_name_without_ext}.png")

        download_and_convert(img_url, file_name)

    return img_tag


def scrape_images(search_query):
    unsplash_url = f"https://unsplash.com/s/photos/{search_query}"
    soup = get_soup(unsplash_url)

    # Find all img tags
    img_tags = soup.find_all("img")

    # Filter out only the ones with the correct class (this might change if Unsplash updates their website)
    # img_tags = [img for img in img_tags if img.get('class') and 'tB6UZ a5VGX' in img.get('class')[0]]

    print(
        f"Found {len(img_tags)} images to download..."
    )  # Print the number of images found

    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    workers = min(MAX_WORKERS, len(img_tags))

    with futures.ThreadPoolExecutor(max_workers=workers) as executor:
        res = list(tqdm(executor.map(scrape_one, img_tags), total=len(img_tags)))

    return len(list(res))


def main():
    t0 = time.time()
    count = scrape_images("dog")
    elapsed = time.time() - t0
    # msg = '\n{} dog pics downloaded in {:.2f}s'
    print(f"\n{count} dog pics downloaded in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
