import base64
import os
import time
from io import BytesIO

import requests
from PIL import Image
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_DIR = 'downloaded_images'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}


def get_soup(url):
    response = requests.get(url, headers=HEADERS)
    print(f"Response Code from {url}: {response.status_code}")  # Check response status
    return BeautifulSoup(response.content, 'html.parser')


def download_and_convert(url, output_path):
    if url.startswith("data:image"):
        # Handle base64 encoded images
        image_format = url.split(';')[0].split('/')[-1]
        image_b64 = url.split(",")[1]
        image_data = base64.b64decode(image_b64)

        with open(output_path, 'wb') as f:
            f.write(image_data)
    else:
        # Handle regular image URLs
        response = requests.get(url)

        # Check if the content type indicates it's an image
        if 'image' not in response.headers.get('Content-Type', ''):
            print(f"Skipping non-image URL: {url}")
            return

        image = Image.open(BytesIO(response.content))
        image.save(output_path, 'PNG')


def scrape_images_from_unsplash(search_query):
    unsplash_url = f"https://unsplash.com/s/photos/{search_query}"
    soup = get_soup(unsplash_url)

    # Find all img tags
    img_tags = soup.find_all('img')

    # Filter out only the ones with the correct class (this might change if Unsplash updates their website)
    # img_tags = [img for img in img_tags if img.get('class') and 'tB6UZ a5VGX' in img.get('class')[0]]

    print(f"Found {len(img_tags)} images to download...")  # Print the number of images found

    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    for idx, img_tag in tqdm(enumerate(img_tags), total=len(img_tags), desc="Downloading images"):
        img_url = img_tag.get('src')
        if img_url:
            file_name = os.path.join(BASE_DIR, f"{search_query}_{idx}.png")
            download_and_convert(img_url, file_name)

    return len(img_tags)

def main():
    t0 = time.time()
    count = scrape_images_from_unsplash("dog")
    elapsed = time.time() - t0
    # msg = '\n{} dog pics downloaded in {:.2f}s'
    print(f'\n{count} dog pics downloaded in {elapsed:.2f}s')

if __name__ == "__main__":
    main()
