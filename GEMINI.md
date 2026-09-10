# Strait Watch Compass Project Guidelines & Rules

This document outlines the coding standards, architectural rules, and development practices for the **Strait Watch Compass (台海動態羅盤)** project.

---

## 1. Mobile & Web Compatibility Guidelines

### 1.1 LocalStorage Quota Safety
- **Strict Quota Limit**: Mobile Safari (iOS) and Mobile Chrome (Android) enforce a strict ~5MB quota limit for `localStorage`.
- **Try-Catch Wrapping**: All `localStorage.setItem` calls must be wrapped in `try...catch (err)` blocks to prevent `QuotaExceededError` exceptions from stopping JavaScript execution on page load.
- **Graceful Fallbacks**: If saving to `localStorage` fails, fall back to in-memory window variables without blocking page initialization or view switching.

### 1.2 IIFE Global Function Exports
- **Global Scope Exposure**: When wrapping application logic inside an IIFE `(function() { ... })()`, all functions called by HTML `onclick`, `onchange`, or external event handlers (e.g. `setStage`, `applyTheme`, `exportData`, `clearAllData`) **must be explicitly exposed** on the `window` object:
  ```javascript
  window.setStage = setStage;
  window.applyTheme = applyTheme;
  ```
- **Avoid Scoping Errors**: Prevent `ReferenceError: function is not defined` when interactive elements trigger inline JS handlers on mobile or desktop browsers.

### 1.3 SVG Touch & Pointer Events
- **Child Element Interception**: SVG child elements (`<circle>`, `<path>`, `<text>`, `<rect>`) inside interactive components (e.g., compass logo, interactive map icons) can intercept pointer/touch events.
- **Pointer-Events CSS**: Ensure interactive SVG nodes disable pointer events on internal elements using `.compass-node * { pointer-events: none !important; }` or handle event delegation using both `click` and `touchstart` event listeners.

---

## 2. Navigation & UI State Management

- **Default Landing Stage**: Initial page render should default to the primary analytical view (`analyze` stage) while maintaining navigation state across mobile nav bar buttons (`📝 紀錄`, `🗂️ 分類`, `📈 分析`, `📑 報告`, `❓ 說明`).
- **Responsive Layout**: Maintain dual support for desktop sidebar navigation (`.nav-item`) and mobile sticky navigation bar (`.mobile-nav-bar`).

---

## 3. Data Scraping & Pipeline

- **Scraper Script**: `mnd_scraper.py` fetches military activity reports from MND. Daily updates write to both `records.js` (`const DATASET = [...]`) and `records.json`.
- **GitHub Actions Workflow**: `.github/workflows/daily_scrape.yml` uses `actions/setup-python@v5` to automate scraping and auto-commit changes back to `main`.
- **Cache Control**: Prevent stale asset caching on GitHub Pages using `<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">` in `index.html` and `strait-watch-compass.html`.
