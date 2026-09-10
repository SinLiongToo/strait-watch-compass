---
name: strait-watch-compass-dev
description: >-
  Development, testing, data scraping pipeline, and deployment procedures for the Strait Watch Compass (台海動態羅盤) project. Use when modifying or debugging UI navigation, mobile local storage safety, dataset scrapers, or GitHub Actions workflows in this repository.
---

# Strait Watch Compass Development & Maintenance

This skill documents standard operating procedures for developing, testing, scraping military activity data, and deploying the **Strait Watch Compass (台海動態羅盤)** application.

## 1. Environment & Setup

- **Project Root**: `SinLiongToo/strait-watch-compass`
- **Main HTML Entry Points**: `index.html` and `strait-watch-compass.html`
- **Dataset File**: `records.js` (defines `window.INITIAL_RECORDS` / `const DATASET`) and `records.json`

## 2. Scraping & Data Pipeline

To execute the MND data scraper locally:
```bash
python mnd_scraper.py 5
```
- Parameters:
  - `5`: Scrapes latest 5 pages of announcements.
  - `all`: Full re-scrape of all historical announcements.
- Output: Automatically updates `records.js` and `records.json`.

## 3. Mobile Compatibility Audit Checklist

Before releasing any frontend changes:
1. **LocalStorage & IndexedDB Safety**: Verify all `localStorage.setItem` calls are inside `try...catch` blocks and `IndexedDB` (`StraitWatchCompassDB`) is used for high-volume record persistence to prevent `QuotaExceededError` crashes on mobile devices with 5MB limits.
2. **Webpage Update Timestamp Badge**: Verify that `updateLastUpdateBadge()` correctly renders the latest record date and total count in `#datasetUpdateBadge`.
3. **IIFE Window Exports**: Verify that functions invoked by inline DOM attributes (`onclick`, `onchange`) are attached to `window` (e.g., `window.setStage`, `window.applyTheme`).
4. **SVG Pointer Events**: Ensure interactive SVG icons pass pointer events through or set `pointer-events: none` on child elements.
5. **Mobile Navigation**: Test tab switching between `Record`, `Categorize`, `Analyze`, `Report`, and `Help` on mobile viewport widths (<768px).

## 4. CI/CD & Deployment

- **GitHub Workflow**: `.github/workflows/daily_scrape.yml`
- **Python Setup Step**: Must use `actions/setup-python@v5`.
- **Git Push Verification**:
  ```bash
  git status
  git add .
  git commit -m "Update rules and skills"
  git push origin main
  ```
- Live Site: `https://sinliongtoo.github.io/strait-watch-compass/`
