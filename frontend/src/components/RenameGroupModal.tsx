import { useState } from "react";

interface Props {
  groupName: string;
  onCancel: () => void;
  onConfirm: (newName: string) => void;
}

export default function RenameGroupModal({ groupName, onCancel, onConfirm }: Props) {
  const [value, setValue] = useState(groupName);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || trimmed === groupName) {
      onCancel();
      return;
    }
    onConfirm(trimmed);
  };
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <form className="modal" role="dialog" aria-modal="true" onSubmit={submit}>
        <h3 className="modal-title">Rename group "{groupName}"</h3>
        <p className="muted modal-body">
          The new name will apply to every ratio currently in this group.
        </p>
        <input
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="New group name"
          required
        />
        <div className="modal-actions" style={{ marginTop: 14 }}>
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit">Rename</button>
        </div>
      </form>
    </div>
  );
}
