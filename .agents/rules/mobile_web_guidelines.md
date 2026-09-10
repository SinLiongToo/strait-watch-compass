# Mobile Web Guidelines for Strait Watch Compass

Guidelines for preventing mobile freezing, local storage quota crashes, IIFE scoping errors, and touch interaction issues on iOS and Android devices.

## 1. LocalStorage Quota Management
- Mobile browsers enforce a ~5MB `localStorage` limit.
- **Rule**: Never call `localStorage.setItem` directly without a `try...catch` block.
- **Example**:
  ```javascript
  try {
    localStorage.setItem('swc_records', JSON.stringify(records));
  } catch (err) {
    console.warn("localStorage quota exceeded or disabled, keeping state in memory:", err);
  }
  ```

## 2. IIFE Scope & Window Exports
- Functions inside anonymous closures or IIFEs must be explicitly assigned to `window` if called by inline DOM events or dynamic scripts.
- **Example**:
  ```javascript
  window.setStage = function(stage) { ... };
  window.applyTheme = function(theme) { ... };
  ```

## 3. Touch Event & Pointer Event Delegation
- On mobile devices, SVG elements and nested child nodes can intercept tap events.
- Disable pointer events on internal decorative elements:
  ```css
  .compass-node * {
    pointer-events: none !important;
  }
  ```
- Support both `click` and `touchstart` event delegation where appropriate.

## 4. IndexedDB & UI Timestamp Badge
- Use IndexedDB (`StraitWatchCompassDB` / `records_store`) to persist dataset records across sessions without quota limits.
- Keep header badge (`datasetUpdateBadge`) updated with latest dataset date and total record count.
