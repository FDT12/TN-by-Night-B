import asyncio
import csv
import re
import os
from datetime import datetime
from playwright.async_api import async_playwright


TUNISIAN_CITIES = [
    'Tunis', 'Ariana', 'Ben Arous', 'Manouba', 'Nabeul', 'Zaghouan',
    'Bizerte', 'Béja', 'Jendouba', 'Kef', 'Siliana', 'Sousse',
    'Monastir', 'Mahdia', 'Sfax', 'Kairouan', 'Kasserine', 'Sidi Bouzid',
    'Gabès', 'Medenine', 'Tataouine', 'Gafsa', 'Tozeur', 'Kebili'
]

CITY_ALIASES = {
    'monastir': 'Monastir',
    'mehdia': 'Mahdia',
    'mahdia': 'Mahdia',
    'sfax': 'Sfax',
    'sousse': 'Sousse',
    'kairouan': 'Kairouan',
}

VENUE_CITY_MAP = {
    'théâtre municipal': 'Tunis',
    'theatre municipal': 'Tunis',
    'colisée': 'Tunis',
    '4ème art': 'Tunis',
    'africa art center': 'Tunis',
    'complexe culturel sfax': 'Sfax',
    'maison de la culture mahdia': 'Mahdia',
    'maison de la culture monastir': 'Monastir',
}


async def extract_city_from_event_page(page, event_url, event_name=None):
    """
    Extract city using deterministic priority:
    1. Event title
    2. Address blocks
    3. Venue mapping
    """

    try:
        await page.goto(event_url, wait_until='domcontentloaded', timeout=15000)
        await page.wait_for_timeout(1000)

        # 1️⃣ TITLE-BASED EXTRACTION (MOST RELIABLE)
        if event_name:
            lowered = event_name.lower()
            for key, city in CITY_ALIASES.items():
                if re.search(rf'\b{key}\b', lowered):
                    return city

        # 2️⃣ ADDRESS / LOCATION BLOCKS ONLY
        address_selectors = [
            'div[class*="address"]',
            'div[class*="location"]',
            'span[class*="address"]',
            'p[class*="address"]',
        ]

        for selector in address_selectors:
            blocks = await page.query_selector_all(selector)
            for block in blocks:
                text = (await block.inner_text()).lower()
                for city in TUNISIAN_CITIES:
                    if re.search(rf'\b{city.lower()}\b', text):
                        return city

        # 3️⃣ VENUE → CITY MAPPING
        venue_blocks = await page.query_selector_all(
            'div[class*="venue"], div.short_info, p'
        )

        for block in venue_blocks:
            text = (await block.inner_text()).lower()
            for venue, city in VENUE_CITY_MAP.items():
                if venue in text:
                    return city

        return 'Unknown'

    except Exception as e:
        print(f"✗ City extraction error: {str(e)[:80]}")
        return 'Error'


async def scrape_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        )
        page = await context.new_page()

        await page.goto(
            'https://teskerti.tn/category/spectacle',
            wait_until='networkidle',
            timeout=60000
        )

        await page.wait_for_selector('div.tour_container', timeout=15000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)

        load_more = await page.query_selector('#load_more')
        if load_more and await load_more.is_visible():
            await load_more.click()
            await page.wait_for_timeout(3000)

        containers = await page.query_selector_all('div.tour_container')
        events = []
        seen_urls = set()

        for container in containers:
            link = await container.query_selector('.img_container a')
            if not link:
                continue

            href = await link.get_attribute('href')
            if not href:
                continue

            if not href.startswith('http'):
                href = f"https://teskerti.tn{href}"

            if href in seen_urls:
                continue

            seen_urls.add(href)

            title_el = (
                await container.query_selector('.tour_title h3 strong')
                or await container.query_selector('.tour_title h3')
            )

            place_el = await container.query_selector('.short_info')
            date_el = await container.query_selector('.rating small')
            price_el = await container.query_selector('.short_info .price')

            events.append({
                'name': (await title_el.inner_text()).strip() if title_el else 'Unknown',
                'place': (await place_el.inner_text()).split('\n')[0].strip() if place_el else 'N/A',
                'date': (await date_el.inner_text()).strip() if date_el else 'N/A',
                'price': (await price_el.inner_text()).strip() if price_el else 'N/A',
                'url': href,
                'city': 'Pending',
                'scraped_at': datetime.now().isoformat()
            })

        print(f"✓ Extracted {len(events)} events")

        for i, event in enumerate(events, 1):
            print(f"[{i}/{len(events)}] {event['name'][:40]}")
            city = await extract_city_from_event_page(
            page,
            event['url'],
            event['name']
            )

            # IMPLICIT TUNIS RULE
            if city == 'Unknown':
                city = 'Tunis'

            event['city'] = city

            await page.wait_for_timeout(400)

        await browser.close()
        return events


async def save_to_csv(events, filename='events.csv'):
    if not events:
        print("⚠ No events to save")
        return None

    fieldnames = [
        'name', 'place', 'date', 'price',
        'url', 'city', 'scraped_at'
    ]

    final_filename = filename

    if os.path.exists(filename):
        try:
            os.remove(filename)
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"events_{timestamp}.csv"
            print(f"⚠ File in use, saving as {final_filename}")

    try:
        with open(final_filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(events)

        print(f"✓ Saved {len(events)} events to {final_filename}")
        return final_filename

    except PermissionError as e:
        print(f"✗ Still cannot write file: {e}")
        return None



async def main():
    events = await scrape_events()
    await save_to_csv(events)


if __name__ == "__main__":
    asyncio.run(main())
