# Sector Rotations Dashboard (frontend)

React + Vite + TypeScript. Talks to the FastAPI backend in `../api`.

## Setup

```bash
cd frontend
cp .env.example .env       # adjust VITE_API_BASE_URL if needed
npm install
npm run dev                # http://localhost:5173
```

The API must be running and have `CORS_ORIGINS` covering the dev URL (the
default already includes `http://localhost:5173`).

## Layout

- **Main panel** — one heatmap per selected group, x = date, y = ratio,
  cell = % change of the ratio from the first bar in the window.
- **Right rail top** — multi-select of existing groups (from `GET /groups`)
  plus a `+ new ratio` toggle.
- **Right rail middle** — form for `POST /ratios` (numerator_stock,
  denominator_stock, group_name). Visible only when `+ new ratio` is toggled.

## Charts

Apache ECharts via `echarts-for-react`. One library, many chart types — the
heatmap is built-in and the same library covers line/candlestick/bar/scatter
when we add more views.
