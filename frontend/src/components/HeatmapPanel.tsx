import { useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import type { GroupResponse, RatioSeries } from "../api/types";

interface Props {
  name: string;
  data: GroupResponse | undefined;
  error?: string;
  onDeleteRatio: (id: number, label: string) => void;
  onTogglePin: (id: number, pinned: boolean) => void;
  onReorder: (groupName: string, ratioIds: number[]) => void;
}

// Build an ECharts heatmap option from a group's ratio time series, in the
// exact order they appear in `data.ratios`.
function buildOption(data: GroupResponse) {
  const dates = new Set<string>();
  const rowLabels: string[] = [];

  data.ratios.forEach((series) => {
    rowLabels.push(`${series.numerator}/${series.denominator}`);
    series.points.forEach((p) => dates.add(p.date));
  });

  const sortedDates = Array.from(dates).sort();
  const dateIdx = new Map(sortedDates.map((d, i) => [d, i]));

  const cells: [number, number, number][] = [];
  data.ratios.forEach((series, rowIdx) => {
    const base = series.points[0]?.ratio ?? 0;
    series.points.forEach((p) => {
      const x = dateIdx.get(p.date)!;
      const pct = base === 0 ? 0 : ((p.ratio - base) / base) * 100;
      cells.push([x, rowIdx, pct]);
    });
  });

  const absMax = Math.max(1, ...cells.map(([, , v]) => Math.abs(v)));

  return {
    tooltip: {
      position: "top",
      formatter: (params: { value: [number, number, number] }) => {
        const [x, y, v] = params.value;
        return `${rowLabels[y]}<br/>${sortedDates[x]}<br/>${v.toFixed(2)}%`;
      },
    },
    grid: { top: 30, left: 110, right: 30, bottom: 30 },
    xAxis: {
      type: "category",
      data: sortedDates,
      axisLabel: { color: "#8a93a6", fontSize: 10, hideOverlap: true },
      splitArea: { show: false },
    },
    yAxis: {
      type: "category",
      data: rowLabels,
      axisLabel: { color: "#e6e9ef", fontSize: 11 },
      splitArea: { show: false },
    },
    visualMap: {
      min: -absMax,
      max: absMax,
      calculable: false,
      show: false,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      textStyle: { color: "#8a93a6" },
      inRange: {
        color: ["#c0392b", "#e57373", "#1d2230", "#7ed6a4", "#27ae60"],
      },
    },
    series: [
      {
        name: data.group,
        type: "heatmap",
        data: cells,
        progressive: 0,
        emphasis: { itemStyle: { borderColor: "#fff", borderWidth: 1 } },
      },
    ],
  };
}

export default function HeatmapPanel({
  name,
  data,
  error,
  onDeleteRatio,
  onTogglePin,
  onReorder,
}: Props) {
  const [dragId, setDragId] = useState<number | null>(null);
  const [overId, setOverId] = useState<number | null>(null);

  const option = useMemo(() => (data ? buildOption(data) : null), [data]);

  if (error) {
    return (
      <div className="heatmap-card">
        <div className="heatmap-title">{name}</div>
        <div className="muted">Failed to load. See toast for details.</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="heatmap-card">
        <div className="heatmap-title">{name}</div>
        <div className="muted">Loading…</div>
      </div>
    );
  }

  const handleDrop = (target: RatioSeries) => {
    if (dragId === null || dragId === target.id) {
      setDragId(null);
      setOverId(null);
      return;
    }
    const ids = data.ratios.map((r) => r.id);
    const from = ids.indexOf(dragId);
    const to = ids.indexOf(target.id);
    if (from === -1 || to === -1) return;
    const next = ids.slice();
    next.splice(from, 1);
    next.splice(to, 0, dragId);
    setDragId(null);
    setOverId(null);
    if (next.some((id, i) => id !== ids[i])) {
      onReorder(name, next);
    }
  };

  const ratioPills = (
    <ul className="ratio-row-list">
      {data.ratios.map((r) => {
        const label = `${r.numerator}/${r.denominator}`;
        const classes = [
          r.pinned ? "pinned" : "",
          dragId === r.id ? "dragging" : "",
          overId === r.id ? "drag-over" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <li
            key={r.id}
            className={classes || undefined}
            draggable
            onDragStart={(e) => {
              setDragId(r.id);
              e.dataTransfer.effectAllowed = "move";
              e.dataTransfer.setData("text/plain", String(r.id));
            }}
            onDragOver={(e) => {
              e.preventDefault();
              e.dataTransfer.dropEffect = "move";
              if (overId !== r.id) setOverId(r.id);
            }}
            onDragLeave={() => {
              if (overId === r.id) setOverId(null);
            }}
            onDrop={(e) => {
              e.preventDefault();
              handleDrop(r);
            }}
            onDragEnd={() => {
              setDragId(null);
              setOverId(null);
            }}
            title="Drag to reorder"
          >
            <span className="drag-handle" aria-hidden>⋮⋮</span>
            <span>{label}</span>
            <button
              type="button"
              className={`icon pin ${r.pinned ? "active" : ""}`}
              onClick={() => onTogglePin(r.id, !r.pinned)}
              title={r.pinned ? "Unpin" : "Pin to top"}
              aria-label={r.pinned ? `Unpin ${label}` : `Pin ${label}`}
              aria-pressed={r.pinned}
            >
              {r.pinned ? "★" : "☆"}
            </button>
            <button
              type="button"
              className="icon remove"
              onClick={() => onDeleteRatio(r.id, label)}
              title={`Delete ${label}`}
              aria-label={`Delete ${label}`}
            >
              −
            </button>
          </li>
        );
      })}
    </ul>
  );

  const hasPoints = data.ratios.some((r) => r.points.length > 0);
  if (!hasPoints) {
    return (
      <div className="heatmap-card">
        <div className="heatmap-title">
          {name}{" "}
          <span className="muted">
            · {data.ratios.length} ratios · {data.days}d
          </span>
        </div>
        {ratioPills}
        <div className="muted">
          No overlapping bars in the selected window. Try widening the days range.
        </div>
      </div>
    );
  }

  const height = Math.max(180, 40 * data.ratios.length + 100);
  return (
    <div className="heatmap-card">
      <div className="heatmap-title">
        {name} <span className="muted">· {data.ratios.length} ratios · {data.days}d</span>
      </div>
      {ratioPills}
      {option && (
        <ReactECharts
          option={option}
          style={{ height, width: "100%" }}
          notMerge
          lazyUpdate
        />
      )}
    </div>
  );
}
