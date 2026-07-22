import urllib.request
import re
import json
import os
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thread limit to avoid getting blocked by MND's WAF
MAX_WORKERS = 5

def fetch_url(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    # Retry logic
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if attempt == 2:
                print(f"Error fetching {url} after 3 attempts: {e}", file=sys.stderr)
                return None
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

def strip_html_tags(html):
    html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.I)
    html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_roc_date(roc_date_str):
    # e.g., "115.04.20"
    m = re.search(r'(\d{2,3})\.(\d{2})\.(\d{2})', roc_date_str)
    if m:
        year = int(m.group(1)) + 1911
        month = int(m.group(2))
        day = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None

def parse_detail(id_val, date_str):
    url = f"https://www.mnd.gov.tw/Publish.aspx?p={id_val}&title=%e6%96%b0%e8%81%9e%e8%88%87%e5%85%ac%e5%91%8a&SelectStyle=%e5%8d%b3%e6%99%82%e8%bb%8d%e4%ba%8b%e5%8b%95%e6%85%8b"
    html = fetch_url(url)
    if not html:
        return []

    text = strip_html_tags(html)
    
    # Double check Date if not provided
    if not date_str:
        date_match = re.search(r'日期[：\s]*(中華民國)?\s*(\d+)年\s*(\d+)月\s*(\d+)日', text)
        if date_match:
            is_roc = date_match.group(1) is not None or "中華民國" in date_match.group(0)
            year = int(date_match.group(2))
            if is_roc:
                year += 1911
            month = int(date_match.group(3))
            day = int(date_match.group(4))
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
        else:
            title_match = re.search(r'(\d+)\.(\d+)\.(\d+)', text)
            if title_match:
                year = int(title_match.group(1)) + 1911
                month = int(title_match.group(2))
                day = int(title_match.group(3))
                date_str = f"{year:04d}-{month:02d}-{day:02d}"

    if not date_str:
        print(f"Skipping ID {id_val}: Date not found", file=sys.stderr)
        return []

    results = []

    # Check format: post-2022 uses "迄0600時止，偵獲共機X架次..." paragraph style
    is_modern = "迄" in text and "時止" in text and "偵獲" in text
    
    if is_modern:
        activity_match = re.search(r'迄\s*\d+\s*時止\s*，\s*偵獲[^。]+持續在[臺台]海周邊活動', text)
        notes = ""
        if activity_match:
            notes = activity_match.group(0).strip()
        else:
            fallback_match = re.search(r'偵獲共[機艦].+?持續在[臺台]海周邊活動', text)
            notes = fallback_match.group(0).strip() if fallback_match else text

        drone_count = 0
        drone_match = re.search(r'無人機\s*(\d+)\s*架次', notes)
        if drone_match:
            drone_count = int(drone_match.group(1))
            results.append({
                "date": date_str,
                "type": "drone",
                "count": drone_count,
                "location": "台海周邊空域",
                "notes": notes,
                "source": "中華民國國防部"
            })

        air_match = re.search(r'共機\s*(\d+)\s*架次', notes)
        if air_match:
            air_count = int(air_match.group(1))
            if drone_count > 0 and re.search(r'共機\s*\d+\s*架次.*?[（\(].*?無人機', notes):
                air_count = max(0, air_count - drone_count)
            
            loc = "台海周邊空域"
            loc_match = re.search(r'共機\s*\d+\s*架次\s*[（\(]([^）\)]+)[）\)]', notes)
            if loc_match:
                loc = loc_match.group(1).strip()
                
            if air_count > 0:
                results.append({
                    "date": date_str,
                    "type": "air",
                    "count": air_count,
                    "location": loc,
                    "notes": notes,
                    "source": "中華民國國防部"
                })

        ship_match = re.search(r'共艦\s*(\d+)\s*艘', notes)
        if ship_match:
            ship_count = int(ship_match.group(1))
            results.append({
                "date": date_str,
                "type": "ship",
                "count": ship_count,
                "location": "台海周邊海域",
                "notes": notes,
                "source": "中華民國國防部"
            })

        vessel_match = re.search(r'公務船\s*(\d+)\s*艘', notes)
        if vessel_match:
            vessel_count = int(vessel_match.group(1))
            results.append({
                "date": date_str,
                "type": "vessel",
                "count": vessel_count,
                "location": "台海周邊海域",
                "notes": notes,
                "source": "中華民國國防部"
            })

        balloon_match = re.search(r'氣球\s*(\d+)\s*[枚顆]', notes)
        if balloon_match:
            balloon_count = int(balloon_match.group(1))
            results.append({
                "date": date_str,
                "type": "balloon",
                "count": balloon_count,
                "location": "台海周邊空域",
                "notes": notes,
                "source": "中華民國國防部"
            })
            
    else:
        # Format B (Older list-style, e.g. "二、機型 運8反潛機2架次")
        model_section_match = re.search(r'機型\s*(.*?)\s*(?:活動概要|四、)', text)
        model_text = model_section_match.group(1) if model_section_match else text
        
        counts = [int(c) for c in re.findall(r'(\d+)\s*架次', model_text)]
        total_air = sum(counts)
        
        if total_air > 0:
            results.append({
                "date": date_str,
                "type": "air",
                "count": total_air,
                "location": "我西南防空識別區",
                "notes": text[:1000],
                "source": "中華民國國防部"
            })
            
    return results

def scrape_list_page(page):
    base_list_url = "https://www.mnd.gov.tw/news/plaactlist"
    url = base_list_url if page == 1 else f"{base_list_url}/{page}"
    html = fetch_url(url)
    if not html:
        return []
    
    # Extract links and inner text to map IDs to dates
    a_tags = re.findall(r'<a\b[^>]*href=["\']([^"\']*(?:plaact|Publish\.aspx)[^"\']*)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
    
    page_items = []
    for href, inner_text in a_tags:
        id_match = re.search(r'(?:plaact/|p=)(\d+)', href)
        if id_match:
            id_val = id_match.group(1)
            # Remove HTML tags inside link text if any, and parse Date
            clean_text = strip_html_tags(inner_text)
            date_str = parse_roc_date(clean_text)
            if date_str:
                page_items.append((id_val, date_str))
    return page_items

def scrape_mnd(num_pages=230):
    print(f"Starting sweep for {num_pages} index pages...")
    
    # Load existing database if available
    existing_records = []
    existing_dates = set()
    json_path = 'records.json'
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_records = json.load(f)
                existing_dates = {r['date'] for r in existing_records}
            print(f"Loaded {len(existing_records)} existing records from cache ({len(existing_dates)} unique dates).")
        except Exception as e:
            print(f"Error loading existing cache: {e}. Starting fresh.")

    # Step 1: Concurrently fetch list pages to build ID -> Date mapping
    all_mappings = {}
    print(f"Fetching index pages 1 to {num_pages} concurrently...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_list_page, p): p for p in range(1, num_pages + 1)}
        for fut in as_completed(futures):
            page_num = futures[fut]
            items = fut.result()
            for id_val, date_str in items:
                all_mappings[id_val] = date_str
    
    print(f"Discovered {len(all_mappings)} total articles across all index pages.")
    
    # Step 2: Filter out IDs whose dates we already have
    pending_items = []
    skipped_count = 0
    for id_val, date_str in all_mappings.items():
        if date_str in existing_dates:
            skipped_count += 1
        else:
            pending_items.append((id_val, date_str))
            
    print(f"Cache hit: skipped {skipped_count} articles. Remaining to fetch: {len(pending_items)}")
    
    if not pending_items:
        print("All articles already cached! No new detail pages to fetch.")
        return existing_records

    # Step 3: Concurrently fetch and parse remaining detail pages
    new_records = []
    print(f"Fetching {len(pending_items)} detail pages concurrently (workers={MAX_WORKERS})...")
    
    counter = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(parse_detail, item[0], item[1]): item for item in pending_items}
        for fut in as_completed(futures):
            item = futures[fut]
            res = fut.result()
            if res:
                new_records.extend(res)
            counter += 1
            if counter % 50 == 0:
                print(f"  Progress: {counter}/{len(pending_items)} detail pages processed...")
                
    # Step 4: Combine, deduplicate, and sort records
    combined_records = existing_records + new_records
    
    # Deduplicate
    seen = set()
    deduped_records = []
    for r in combined_records:
        key = (r['date'], r['type'], r['count'])
        if key not in seen:
            seen.add(key)
            deduped_records.append(r)
            
    # Sort descending
    deduped_records.sort(key=lambda r: r['date'], reverse=True)
    return deduped_records

def main():
    num_pages = 230
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'all':
            num_pages = 230
        else:
            try:
                num_pages = int(sys.argv[1])
            except ValueError:
                print("Invalid page count argument, using default (230)")

    records = scrape_mnd(num_pages)
    
    # Save output files
    json_path = 'records.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved {len(records)} total records to {json_path}")
    
    js_path = 'records.js'
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write("window.mnd_records = ")
        json.dump(records, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"Successfully saved records as JS helper to {js_path}")

if __name__ == "__main__":
    main()
