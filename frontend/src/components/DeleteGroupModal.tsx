interface Props {
  groupName: string;
  onCancel: () => void;
  onConfirm: (cascade: boolean) => void;
}

export default function DeleteGroupModal({ groupName, onCancel, onConfirm }: Props) {
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true">
        <h3 className="modal-title">Delete group "{groupName}"?</h3>
        <p className="muted modal-body">
          Detach keeps the ratios and only clears their group. Delete removes
          the ratios entirely.
        </p>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" onClick={() => onConfirm(false)}>
            Detach
          </button>
          <button type="button" className="danger" onClick={() => onConfirm(true)}>
            Delete ratios
          </button>
        </div>
      </div>
    </div>
  );
}
