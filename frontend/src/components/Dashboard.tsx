import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "../api/client";
import type { GroupListItem, GroupResponse } from "../api/types";
import DeleteGroupModal from "./DeleteGroupModal";
import HeatmapPanel from "./HeatmapPanel";
import RenameGroupModal from "./RenameGroupModal";
import Sidebar from "./Sidebar";

export default function Dashboard() {
  const [groups, setGroups] = useState<GroupListItem[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [groupData, setGroupData] = useState<Record<string, GroupResponse>>({});
  const [groupErrors, setGroupErrors] = useState<Record<string, true>>({});
  const [days, setDays] = useState<number>(120);
  const [reloadTick, setReloadTick] = useState(0);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [pendingRename, setPendingRename] = useState<string | null>(null);

  const refreshGroups = useCallback(async () => {
    try {
      const items = await api.listGroups();
      setGroups(items);
    } catch (err) {
      toast.error(`Failed to load groups: ${(err as Error).message}`);
    }
  }, []);

  useEffect(() => {
    refreshGroups();
  }, [refreshGroups]);

  // Re-fetch series whenever the selection, window, or reloadTick changes.
  // Each group's request is independent so one failure doesn't take down others.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      const nextData: Record<string, GroupResponse> = {};
      const nextErrors: Record<string, true> = {};
      await Promise.all(
        selected.map(async (name) => {
          try {
            nextData[name] = await api.getGroup(name, days);
          } catch (err) {
            nextErrors[name] = true;
            toast.error(`${name}: ${(err as Error).message}`);
          }
        }),
      );
      if (!cancelled) {
        setGroupData(nextData);
        setGroupErrors(nextErrors);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selected, days, reloadTick]);

  const toggle = (name: string) => {
    setSelected((cur) =>
      cur.includes(name) ? cur.filter((n) => n !== name) : [...cur, name],
    );
  };

  const refetchAll = () => setReloadTick((t) => t + 1);

  const handleRatioAdded = async (groupName: string | null) => {
    await refreshGroups();
    if (groupName && selected.includes(groupName)) refetchAll();
  };

  const handleDeleteRatio = async (id: number, label: string) => {
    if (!window.confirm(`Delete ratio ${label}?`)) return;
    try {
      await api.deleteRatio(id);
      toast.success(`Deleted ${label}`);
      // The group may now be empty (404) — refresh both list and series.
      await refreshGroups();
      refetchAll();
    } catch (err) {
      toast.error(`Delete failed: ${(err as Error).message}`);
    }
  };

  const handleTickersAdded = async (added: string[]) => {
    // Tickers don't affect groups/ratios directly, but keep the dropdown
    // consistent in case anything is derived from them later.
    await refreshGroups();
    if (added.length && selected.length) refetchAll();
  };

  const handleDeleteGroup = (name: string) => {
    setPendingDelete(name);
  };

  const handleRenameGroup = (name: string) => {
    setPendingRename(name);
  };

  const handleToggleHidden = async (name: string, hidden: boolean) => {
    setGroups((cur) =>
      cur.map((g) => (g.name === name ? { ...g, hidden } : g)),
    );
    if (hidden) setSelected((cur) => cur.filter((n) => n !== name));
    try {
      await api.setGroupHidden(name, hidden);
      toast.success(hidden ? `Hid "${name}"` : `Unhid "${name}"`);
    } catch (err) {
      toast.error(`Visibility update failed: ${(err as Error).message}`);
      await refreshGroups();
    }
  };

  const confirmRenameGroup = async (newName: string) => {
    const oldName = pendingRename;
    if (!oldName) return;
    setPendingRename(null);
    try {
      await api.renameGroup(oldName, newName);
      toast.success(`Renamed "${oldName}" to "${newName}"`);
      setSelected((cur) => cur.map((n) => (n === oldName ? newName : n)));
      await refreshGroups();
      refetchAll();
    } catch (err) {
      toast.error(`Rename failed: ${(err as Error).message}`);
    }
  };

  const confirmDeleteGroup = async (cascade: boolean) => {
    const name = pendingDelete;
    if (!name) return;
    setPendingDelete(null);
    try {
      await api.deleteGroup(name, cascade);
      toast.success(
        cascade
          ? `Deleted group "${name}" and its ratios`
          : `Detached ratios from "${name}"`,
      );
      setSelected((cur) => cur.filter((n) => n !== name));
      await refreshGroups();
      refetchAll();
    } catch (err) {
      toast.error(`Delete failed: ${(err as Error).message}`);
    }
  };

  // Apply the new order locally first so the UI is snappy, then persist. If
  // the server rejects we re-fetch to get authoritative state.
  const handleReorderRatios = async (groupName: string, ratioIds: number[]) => {
    const previous = groupData[groupName];
    if (!previous) return;
    const byId = new Map(previous.ratios.map((r) => [r.id, r]));
    const reordered = ratioIds
      .map((id) => byId.get(id))
      .filter((r): r is NonNullable<typeof r> => r !== undefined);
    setGroupData((cur) => ({
      ...cur,
      [groupName]: { ...previous, ratios: reordered },
    }));
    try {
      await api.reorderGroup(groupName, ratioIds);
    } catch (err) {
      toast.error(`Reorder failed: ${(err as Error).message}`);
      refetchAll();
    }
  };

  const handleTogglePin = async (id: number, pinned: boolean) => {
    // Find which group owns this ratio and apply optimistically: flip the
    // pinned flag and re-sort (pinned first, original order within each
    // bucket).
    const owningGroup = Object.entries(groupData).find(([, g]) =>
      g.ratios.some((r) => r.id === id),
    );
    if (owningGroup) {
      const [gName, g] = owningGroup;
      const updated = g.ratios.map((r) =>
        r.id === id ? { ...r, pinned } : r,
      );
      const stableIdx = new Map(g.ratios.map((r, i) => [r.id, i]));
      const reordered = [...updated].sort((a, b) => {
        if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
        return (stableIdx.get(a.id) ?? 0) - (stableIdx.get(b.id) ?? 0);
      });
      setGroupData((cur) => ({
        ...cur,
        [gName]: { ...g, ratios: reordered },
      }));
    }
    try {
      await api.setRatioPinned(id, pinned);
    } catch (err) {
      toast.error(`Pin failed: ${(err as Error).message}`);
      refetchAll();
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">Sector Rotations Dashboard</div>

      <div className="main-panel">
        {selected.length === 0 && (
          <div className="placeholder">
            Pick one or more groups from the sidebar to view heatmaps.
          </div>
        )}
        {selected.map((name) => (
          <HeatmapPanel
            key={name}
            name={name}
            data={groupData[name]}
            error={groupErrors[name] ? "error" : undefined}
            onDeleteRatio={handleDeleteRatio}
            onTogglePin={handleTogglePin}
            onReorder={handleReorderRatios}
          />
        ))}
      </div>

      <Sidebar
        availableGroups={groups}
        selected={selected}
        onToggle={toggle}
        days={days}
        onDaysChange={setDays}
        onRatioAdded={handleRatioAdded}
        onTickersAdded={handleTickersAdded}
        onDeleteGroup={handleDeleteGroup}
        onRenameGroup={handleRenameGroup}
        onToggleHidden={handleToggleHidden}
      />

      {pendingDelete && (
        <DeleteGroupModal
          groupName={pendingDelete}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDeleteGroup}
        />
      )}

      {pendingRename && (
        <RenameGroupModal
          groupName={pendingRename}
          onCancel={() => setPendingRename(null)}
          onConfirm={confirmRenameGroup}
        />
      )}
    </div>
  );
}
