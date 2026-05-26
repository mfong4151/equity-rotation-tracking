import { useEffect, useMemo, useState } from "react";
import type { GroupListItem } from "../api/types";
import GroupMultiSelect from "./GroupMultiSelect";
import AddRatioForm from "./AddRatioForm";
import AddTickersForm from "./AddTickersForm";

interface Props {
  availableGroups: GroupListItem[];
  selected: string[];
  onToggle: (name: string) => void;
  days: number;
  onDaysChange: (days: number) => void;
  onRatioAdded: (groupName: string | null) => void | Promise<void>;
  onTickersAdded: (added: string[]) => void | Promise<void>;
  onDeleteGroup: (name: string) => void | Promise<void>;
  onRenameGroup: (name: string) => void;
  onToggleHidden: (name: string, hidden: boolean) => void | Promise<void>;
}

const MIN_DAYS = 1;
const MAX_DAYS = 365;

export default function Sidebar({
  availableGroups,
  selected,
  onToggle,
  days,
  onDaysChange,
  onRatioAdded,
  onTickersAdded,
  onDeleteGroup,
  onRenameGroup,
  onToggleHidden,
}: Props) {
  const [showRatioForm, setShowRatioForm] = useState(false);
  const [showTickerForm, setShowTickerForm] = useState(false);
  const [showHidden, setShowHidden] = useState(false);

  const hiddenCount = useMemo(
    () => availableGroups.filter((g) => g.hidden).length,
    [availableGroups],
  );
  const visibleGroups = useMemo(
    () => (showHidden ? availableGroups : availableGroups.filter((g) => !g.hidden)),
    [availableGroups, showHidden],
  );
  const groupNames = useMemo(
    () => availableGroups.map((g) => g.name),
    [availableGroups],
  );

  // Track the input as a free-form string so the user can clear it / type
  // partial values without us snapping the parent state back to a default.
  const [daysInput, setDaysInput] = useState<string>(String(days));

  useEffect(() => {
    setDaysInput((cur) => (Number(cur) === days ? cur : String(days)));
  }, [days]);

  const commitDays = (raw: string) => {
    const trimmed = raw.trim();
    if (trimmed === "") {
      setDaysInput(String(days));
      return;
    }
    const parsed = Number(trimmed);
    if (!Number.isFinite(parsed)) {
      setDaysInput(String(days));
      return;
    }
    const clamped = Math.min(MAX_DAYS, Math.max(MIN_DAYS, Math.round(parsed)));
    setDaysInput(String(clamped));
    if (clamped !== days) onDaysChange(clamped);
  };

  return (
    <aside className="sidebar">
      <div className="card">
        <div className="card-heading">
          <h3>Groups</h3>
          <span
            className="info-tip"
            tabIndex={0}
            aria-label="Heatmap color legend"
          >
            <span className="info-icon" aria-hidden="true">i</span>
            <div className="info-tip-content" role="tooltip">
              <div className="legend-label">Heatmap color scale</div>
              <div className="legend-bar" aria-hidden="true" />
              <div className="legend-ticks">
                <span>−%</span>
                <span>0</span>
                <span>+%</span>
              </div>
              <div className="legend-hint">
                % change vs. the first day in the window.
              </div>
            </div>
          </span>
        </div>
        <GroupMultiSelect
          options={visibleGroups}
          selected={selected}
          onToggle={onToggle}
          onDelete={onDeleteGroup}
          onRename={onRenameGroup}
          onToggleHidden={onToggleHidden}
        />
        {hiddenCount > 0 && (
          <label className="show-hidden">
            <input
              type="checkbox"
              checked={showHidden}
              onChange={(e) => setShowHidden(e.target.checked)}
            />
            Show hidden ({hiddenCount})
          </label>
        )}
        <div style={{ marginTop: 12 }}>
          <label htmlFor="days">Window (days)</label>
          <input
            id="days"
            type="number"
            min={MIN_DAYS}
            max={MAX_DAYS}
            value={daysInput}
            onChange={(e) => setDaysInput(e.target.value)}
            onBlur={(e) => commitDays(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                commitDays((e.target as HTMLInputElement).value);
                (e.target as HTMLInputElement).blur();
              }
            }}
          />
        </div>
        <div className="pill-action-stack">
          <button
            type="button"
            className={`pill-action ${showRatioForm ? "remove" : "add"}`}
            onClick={() => setShowRatioForm((v) => !v)}
            aria-expanded={showRatioForm}
          >
            <span className="pill-icon">{showRatioForm ? "−" : "+"}</span>
            <span>New ratio</span>
          </button>
          <button
            type="button"
            className={`pill-action ${showTickerForm ? "remove" : "add"}`}
            onClick={() => setShowTickerForm((v) => !v)}
            aria-expanded={showTickerForm}
          >
            <span className="pill-icon">{showTickerForm ? "−" : "+"}</span>
            <span>Add tickers</span>
          </button>
        </div>
      </div>

      {showRatioForm && (
        <div className="card">
          <h3>New ratio</h3>
          <AddRatioForm
            knownGroups={groupNames}
            onSubmitted={onRatioAdded}
          />
        </div>
      )}

      {showTickerForm && (
        <div className="card">
          <h3>Add tickers</h3>
          <AddTickersForm
            onAdded={async (added) => {
              await onTickersAdded(added);
              setShowTickerForm(false);
            }}
          />
        </div>
      )}
    </aside>
  );
}
