# 2024 年共軍動態資料補齊與 PDF/圖片 Markdown 轉檔計畫

本計畫旨在補齊國防部 **2024 年全整年（2024-01-12 至 2024-12-31 及 2025 年初）** 之中共解放軍臺海周邊海空域動態數據。由於該期間國防部主要以附件圖片（JPG）與 PDF 形式發布公告，本計畫將運用 Python、PyMuPDF 與 RapidOCR 進行自動化下載、OCR 文字辨識、結構化數據解析，並另存為 `.md` 檔案與更新本系統之 `records.json` 及 `records.js`。

---

## 使用者注意事項 / User Review Required

> [!IMPORTANT]
> 1. 2024 年共有 366 天，國防部公告數量約 370 篇。下載與 OCR 辨識過程約需 2 ~ 3 分鐘。
> 2. 下載之附件檔案（圖片/PDF）將儲存於 `mnd_2024_attachments/` 目錄。
> 3. 轉檔之 Markdown 每日報告將儲存於 `mnd_2024_md/` 目錄，並產生一份全年度總報告 `mnd_2024_md/2024_full_year_report.md` 供使用者直接查閱。

---

## 預計變更與新增內容

### 1. [Scraper 擴充] [mnd_scraper.py](file:///c:/Users/tu-hs/OneDrive/%E6%96%87%E4%BB%B6/2022_0308_MASA/2022-0708/Projects_antigravity/PRC%E5%85%B1%E8%BB%8D%E5%8B%95%E6%85%8B%E5%B9%B2%E6%93%BE/mnd_scraper.py)
- 升級 `parse_detail()`：當內文無純文字時，自動抓取頁面附件 (`File/...` 或 `.pdf`/`.jpg`)。
- 整合 PyMuPDF (PDF 文字提取) 與 RapidOCR (圖片/掃描檔 OCR 文字提取)。
- 自動將辨識後的內文進行正規表示式解析，擷取 `共機`、`無人機`、`共艦`、`氣球`、`公務船` 數量與位置航線。

---

### 2. [資料產出] [NEW] `mnd_2024_attachments/` & [NEW] `mnd_2024_md/`
- **附件資料夾**：完整下載 2024 年國防部發布之 300+ 份每日動態圖檔與 PDF 附件。
- **Markdown 資料夾**：
  - 每日 Markdown 檔 (例如 `mnd_2024_md/2024-08-09.md`)：包含發布日期、原始圖片/附件檔名、OCR 全文、解析後結構化數據。
  - 全年彙整檔 `mnd_2024_md/2024_full_year_report.md`：表格化羅列 2024 每一天的軍機、軍艦、無人機、氣球統計。

---

### 3. [資料庫更新] [records.json](file:///c:/Users/tu-hs/OneDrive/%E6%96%87%E4%BB%B6/2022_0308_MASA/2022-0708/Projects_antigravity/PRC%E5%85%B1%E8%BB%8D%E5%8B%95%E6%85%8B%E5%B9%B2%E6%93%BE/records.json) & [records.js](file:///c:/Users/tu-hs/OneDrive/%E6%96%87%E4%BB%B6/2022_0308_MASA/2022-0708/Projects_antigravity/PRC%E5%85%B1%E8%BB%8D%E5%8B%95%E6%85%8B%E5%B9%B2%E6%93%BE/records.js)
- 將 2024 補齊之全年度紀錄匯入 `records.json` 與 `records.js`。
- 使網頁「台海動態羅盤」的 2024 年折線圖與表格恢復完整連續顯示。

---

### 4. [文件更新] [README.md](file:///c:/Users/tu-hs/OneDrive/%E6%96%87%E4%BB%B6/2022_0308_MASA/2022-0708/Projects_antigravity/PRC%E5%85%B1%E8%BB%8D%E5%8B%95%E6%85%8B%E5%B9%B2%E6%93%BE/README.md)
- 更新說明文件，標註 2024 年資料已透過 RapidOCR / PDF 解析技術成功補齊。

---

## 驗證計畫 (Verification Plan)

### 自動化測試與數據驗證
1. 執行爬蟲及 OCR 處理指令，確認處理天數涵蓋 2024-01-01 至 2024-12-31。
2. 檢查 `records.json` 中 2024 年的不重複日期數 (期望達 350+ 天以上，完整覆蓋 2024 年)。
3. 驗證 `mnd_2024_md/` 下產出的 `.md` 檔案內容完整度。

### 手動驗證
1. 開啟 `strait-watch-compass.html`，切換至「分析 (Analyze)」與「年 (Year)」/「日 (Day)」視角，確認 2024 年資料無斷層。
