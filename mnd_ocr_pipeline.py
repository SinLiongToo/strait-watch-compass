import urllib.request
import urllib.parse
import re
import json
import os
import sys
import html
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import fitz  # PyMuPDF
from rapidocr_onnxruntime import RapidOCR

ocr_engine = None

def get_ocr_engine():
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = RapidOCR()
    return ocr_engine

MAX_WORKERS = 8
ATTACHMENT_DIR = 'mnd_2024_attachments'
MD_DIR = 'mnd_2024_md'

os.makedirs(ATTACHMENT_DIR, exist_ok=True)
os.makedirs(MD_DIR, exist_ok=True)

def fetch_url(url, is_binary=False):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                if is_binary:
                    return content
                return content.decode('utf-8', errors='ignore')
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.0)
    return None

def strip_html_tags(raw_html):
    raw_html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', raw_html, flags=re.I)
    raw_html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', raw_html, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_roc_date(roc_date_str):
    m = re.search(r'(\d{2,3})\.(\d{2})\.(\d{2})', roc_date_str)
    if m:
        year = int(m.group(1)) + 1911
        month = int(m.group(2))
        day = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        text = ""
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text() + "\n"
        except Exception:
            pass
        
        if len(text.strip()) < 20:
            ocr = get_ocr_engine()
            try:
                doc = fitz.open(file_path)
                ocr_texts = []
                for idx, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=150)
                    temp_img = file_path + f"_temp_{idx}.png"
                    pix.save(temp_img)
                    res, _ = ocr(temp_img)
                    if os.path.exists(temp_img):
                        os.remove(temp_img)
                    if res:
                        ocr_texts.append("\n".join([item[1] for item in res]))
                text = "\n".join(ocr_texts)
            except Exception:
                pass
        return text.strip()

    elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
        ocr = get_ocr_engine()
        try:
            res, _ = ocr(file_path)
            if res:
                return "\n".join([item[1] for item in res]).strip()
        except Exception:
            pass
        return ""
    return ""

def parse_records_from_text(text, date_str):
    results = []
    
    if not date_str:
        date_match = re.search(r'民國\s*(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
        if date_match:
            year = int(date_match.group(1)) + 1911
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            date_str = f"{year:04d}-{month:02d}-{day:02d}"

    if not date_str:
        return [], None

    notes = ""
    activity_match = re.search(r'(?:迄|自)[^。]+?\d+時止[，,]\s*偵獲[^。]+持續在[臺台]海周邊活動', text)
    if activity_match:
        notes = activity_match.group(0).strip()
    else:
        fallback_match = re.search(r'偵獲共[機艦].+?持續在[臺台]海周邊活動', text)
        if fallback_match:
            notes = fallback_match.group(0).strip()
        else:
            paras = [p for p in text.split('\n') if '偵獲' in p or '共機' in p or '共艦' in p]
            notes = "；".join(paras) if paras else text[:500]

    notes = re.sub(r'\s+', ' ', notes).strip()

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
        if not loc_match:
            loc_match = re.search(r'其中([^）\)]+空域)', notes)
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

    return results, date_str

def process_article(id_val, date_str):
    url = f"https://www.mnd.gov.tw/Publish.aspx?p={id_val}&title=%e6%96%b0%e8%81%9e%e8%88%87%e5%85%ac%e5%91%8a&SelectStyle=%e5%8d%b3%e6%99%82%e8%bb%8d%e4%ba%8b%e5%8b%95%e6%85%8b"
    raw_html = fetch_url(url)
    if not raw_html:
        return [], None

    html_text = strip_html_tags(raw_html)
    combined_text = html_text
    attachments_downloaded = []

    rel_files = re.findall(r'(?:href|src)=["\']([^"\']*(?:File/|upload/|NewUpload/|\.pdf|\.jpg|\.png|\.jpeg)[^"\']*)["\']', raw_html, re.I)
    
    valid_attachments = []
    for f in rel_files:
        if any(skip in f.lower() for skip in ['plaactlist', 'accesskey', 'logo', 'banner', 'icon', 'css', 'js', 'aa2.1.jpg', 'leader', 'officer', 'video']):
            continue
        valid_attachments.append(f)

    for idx, att_url in enumerate(valid_attachments):
        if not att_url.startswith('http'):
            if att_url.startswith('/'):
                att_url = 'https://www.mnd.gov.tw' + att_url
            else:
                att_url = 'https://www.mnd.gov.tw/' + att_url
        
        parsed_path = urllib.parse.urlparse(att_url).path
        ext = os.path.splitext(parsed_path)[1]
        if not ext:
            ext = '.jpg'
            
        fname = f"{date_str}_{id_val}_{idx+1}_{os.path.basename(parsed_path)}{ext}"
        fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
        local_path = os.path.join(ATTACHMENT_DIR, fname)
        
        if not os.path.exists(local_path):
            data = fetch_url(att_url, is_binary=True)
            if data:
                with open(local_path, 'wb') as f_out:
                    f_out.write(data)
                attachments_downloaded.append(local_path)
        else:
            attachments_downloaded.append(local_path)

    for att_path in attachments_downloaded:
        extracted = extract_text_from_file(att_path)
        if extracted:
            combined_text += "\n" + extracted

    records, parsed_date = parse_records_from_text(combined_text, date_str)
    if not parsed_date:
        parsed_date = date_str

    if parsed_date and parsed_date.startswith('2024'):
        md_file = os.path.join(MD_DIR, f"{parsed_date}.md")
        with open(md_file, 'w', encoding='utf-8') as f_md:
            f_md.write(f"# 國防部中共解放軍臺海周邊海、空域動態報告 ({parsed_date})\n\n")
            f_md.write(f"- **發布日期**: {parsed_date}\n")
            f_md.write(f"- **文章 ID**: {id_val}\n")
            f_md.write(f"- **附件數量**: {len(attachments_downloaded)}\n")
            if attachments_downloaded:
                f_md.write("- **附件列表**:\n")
                for att in attachments_downloaded:
                    f_md.write(f"  - `{os.path.basename(att)}`\n")
            f_md.write("\n## 結構化解析數據\n\n")
            if records:
                f_md.write("| 類型 | 數量 | 位置航線 | 備註 |\n")
                f_md.write("| --- | --- | --- | --- |\n")
                type_map = {'air': '軍機', 'ship': '共艦', 'drone': '無人機', 'balloon': '氣球', 'vessel': '公務船'}
                for r in records:
                    t_str = type_map.get(r['type'], r['type'])
                    f_md.write(f"| {t_str} | {r['count']} | {r['location']} | {r['notes']} |\n")
            else:
                f_md.write("*無偵獲或無結構化數據*\n")
            
            f_md.write("\n## OCR / 內文全文記錄\n\n")
            f_md.write("```text\n")
            f_md.write(combined_text.strip()[:3000])
            f_md.write("\n```\n")

    return records, parsed_date

def scrape_list_page(page):
    url = f"https://www.mnd.gov.tw/news/plaactlist/{page}" if page > 1 else "https://www.mnd.gov.tw/news/plaactlist"
    raw_html = fetch_url(url)
    if not raw_html:
        return []
    
    a_tags = re.findall(r'<a\b[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', raw_html, re.DOTALL | re.IGNORECASE)
    
    page_items = []
    for href, inner_text in a_tags:
        id_match = re.search(r'(?:plaact/|plaactdetail/|p=)(\d+)', href)
        if id_match:
            id_val = id_match.group(1)
            clean_text = strip_html_tags(inner_text)
            date_str = parse_roc_date(clean_text)
            if date_str:
                page_items.append((id_val, date_str))
    return page_items

def run_pipeline(start_page=65, end_page=110):
    print(f"=== Starting MND Scraper & 2024 OCR Pipeline (Pages {start_page} to {end_page}) ===")
    
    existing_records = []
    json_path = 'records.json'
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_records = json.load(f)
            print(f"Loaded {len(existing_records)} existing records.")
        except Exception as e:
            print(f"Error loading existing cache: {e}")

    # Step 1: Sweep index pages
    all_mappings = {}
    print(f"Scanning index pages {start_page} to {end_page}...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_list_page, p): p for p in range(start_page, end_page + 1)}
        for fut in as_completed(futures):
            items = fut.result()
            for id_val, date_str in items:
                if date_str and date_str.startswith('2024'):
                    all_mappings[id_val] = date_str
    
    print(f"Discovered {len(all_mappings)} unique 2024 PLA activity article links.")
    
    pending_items = list(all_mappings.items())
    print(f"Total 2024 articles to process with OCR/PDF parsing: {len(pending_items)}")

    # Step 2: Process detail pages with OCR
    new_records_by_date = {}
    counter = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_article, item[0], item[1]): item for item in pending_items}
        for fut in as_completed(futures):
            recs, d_str = fut.result()
            if d_str and recs:
                if d_str not in new_records_by_date:
                    new_records_by_date[d_str] = []
                new_records_by_date[d_str].extend(recs)
            counter += 1
            if counter % 25 == 0 or counter == len(pending_items):
                print(f"  Progress: {counter}/{len(pending_items)} articles processed...")

    # Step 3: Merge & Deduplicate
    all_recs = []
    for d_str, recs in new_records_by_date.items():
        all_recs.extend(recs)
    
    for r in existing_records:
        if r['date'] not in new_records_by_date:
            all_recs.append(r)
            
    seen = set()
    deduped = []
    for r in all_recs:
        key = (r['date'], r['type'], r['count'], r.get('location', ''))
        if key not in seen:
            seen.add(key)
            deduped.append(r)
            
    deduped.sort(key=lambda r: r['date'], reverse=True)
    
    # Step 4: Save database files
    with open('records.json', 'w', encoding='utf-8') as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(deduped)} total records to records.json")
    
    with open('records.js', 'w', encoding='utf-8') as f:
        f.write("window.mnd_records = ")
        json.dump(deduped, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print("Saved records.js helper file.")

    # Step 5: Generate 2024 full year report
    recs_2024 = [r for r in deduped if r['date'].startswith('2024')]
    dates_2024 = sorted(list({r['date'] for r in recs_2024}))
    
    report_path = os.path.join(MD_DIR, '2024_full_year_report.md')
    with open(report_path, 'w', encoding='utf-8') as f_rep:
        f_rep.write("# 2024 年共軍對台動態全年度總報告 (MND 2024 Full-Year Intelligence Report)\n\n")
        f_rep.write(f"- **總記錄日數量**: {len(dates_2024)} 天\n")
        f_rep.write(f"- **總事件筆數**: {len(recs_2024)} 筆\n")
        
        air_tot = sum(r['count'] for r in recs_2024 if r['type'] == 'air')
        ship_tot = sum(r['count'] for r in recs_2024 if r['type'] == 'ship')
        drone_tot = sum(r['count'] for r in recs_2024 if r['type'] == 'drone')
        balloon_tot = sum(r['count'] for r in recs_2024 if r['type'] == 'balloon')
        vessel_tot = sum(r['count'] for r in recs_2024 if r['type'] == 'vessel')
        
        f_rep.write(f"- **2024 全年總架次/艘次統計**:\n")
        f_rep.write(f"  - ✈️ **共機**: {air_tot} 架次\n")
        f_rep.write(f"  - 🚢 **共艦**: {ship_tot} 艘次\n")
        f_rep.write(f"  - 🛩️ **無人機**: {drone_tot} 架次\n")
        f_rep.write(f"  - 🎈 **氣球**: {balloon_tot} 枚\n")
        f_rep.write(f"  - 🛥️ **公務船**: {vessel_tot} 艘次\n\n")
        
        f_rep.write("## 每日動態彙整明細\n\n")
        f_rep.write("| 日期 | 軍機架次 | 共艦艘次 | 無人機架次 | 氣球枚數 | 公務船艘次 | 主要位置 / 備註 |\n")
        f_rep.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        
        by_date = {}
        for r in recs_2024:
            d = r['date']
            if d not in by_date:
                by_date[d] = {'air': 0, 'ship': 0, 'drone': 0, 'balloon': 0, 'vessel': 0, 'notes': ''}
            by_date[d][r['type']] = by_date[d].get(r['type'], 0) + r['count']
            if r['notes'] and len(r['notes']) > len(by_date[d]['notes']):
                by_date[d]['notes'] = r['notes']
                
        for d in sorted(by_date.keys(), reverse=True):
            info = by_date[d]
            f_rep.write(f"| {d} | {info['air']} | {info['ship']} | {info['drone']} | {info['balloon']} | {info['vessel']} | {info['notes'][:60]}... |\n")

    print(f"Generated 2024 full year report at {report_path}")

if __name__ == '__main__':
    start_p = 65
    end_p = 110
    if len(sys.argv) > 1:
        try:
            start_p = int(sys.argv[1])
            if len(sys.argv) > 2:
                end_p = int(sys.argv[2])
        except ValueError:
            pass
    run_pipeline(start_p, end_p)
