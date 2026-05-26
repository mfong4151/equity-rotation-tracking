import { useEffect, useRef, useState } from "react";
import type { GroupListItem } from "../api/types";

interface Props {
  options: GroupListItem[];
  selected: string[];
  onToggle: (name: string) => void;
  onDelete: (name: string) => void;
  onRename: (name: string) => void;
  onToggleHidden: (name: string, hidden: boolean) => void | Promise<void>;
}

export default function GroupMultiSelect({
  options,
  selected,
  onToggle,
  onDelete,
  onRename,
  onToggleHidden,
}: Props) {
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onDocClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(null);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(null);
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  if (options.length === 0) {
    return (
      <p className="muted">
        No groups yet. Add a ratio with a group name to populate this list.
      </p>
    );
  }

  return (
    <ul className="group-list">
      {options.map((g) => {
        const name = g.name;
        const checked = selected.includes(name);
        const isMenuOpen = menuOpen === name;
        const classes = [
          checked ? "selected" : "",
          g.hidden ? "hidden-group" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <li key={name} className={classes || undefined}>
            <span className="group-name">{name}</span>
            <button
              type="button"
              className="icon add"
              onClick={() => {
                if (!checked) onToggle(name);
              }}
              disabled={checked || g.hidden}
              aria-label={`Show ${name}`}
              title={g.hidden ? "Unhide group to show" : `Show ${name}`}
            >
              +
            </button>
            <button
              type="button"
              className="icon remove"
              onClick={() => onDelete(name)}
              aria-label={`Delete ${name}`}
              title={`Delete group ${name}`}
            >
              −
            </button>
            <div className="kebab-wrap" ref={isMenuOpen ? menuRef : undefined}>
              <button
                type="button"
                className="icon kebab"
                onClick={() => setMenuOpen(isMenuOpen ? null : name)}
                aria-haspopup="menu"
                aria-expanded={isMenuOpen}
                aria-label={`More actions for ${name}`}
                title="More actions"
              >
                ⋮
              </button>
              {isMenuOpen && (
                <div className="popover-menu" role="menu">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(null);
                      onRename(name);
                    }}
                  >
                    Rename…
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(null);
                      onToggleHidden(name, !g.hidden);
                    }}
                  >
                    {g.hidden ? "Unhide" : "Hide"}
                  </button>
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
