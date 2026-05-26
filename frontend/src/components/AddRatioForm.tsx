import { useState } from "react";
import { toast } from "sonner";
import { api } from "../api/client";

interface Props {
  knownGroups: string[];
  onSubmitted: (groupName: string | null) => void | Promise<void>;
}

const NEW_GROUP = "__new__";
const NO_GROUP = "";

export default function AddRatioForm({ knownGroups, onSubmitted }: Props) {
  const [numerator, setNumerator] = useState("");
  const [denominator, setDenominator] = useState("");
  const [groupChoice, setGroupChoice] = useState<string>(NO_GROUP);
  const [newGroupName, setNewGroupName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const resolveGroup = (): string | null => {
    if (groupChoice === NO_GROUP) return null;
    if (groupChoice === NEW_GROUP) {
      const trimmed = newGroupName.trim();
      return trimmed === "" ? null : trimmed;
    }
    return groupChoice;
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (groupChoice === NEW_GROUP && newGroupName.trim() === "") {
      toast.error("Enter a name for the new group, or pick an existing one.");
      return;
    }
    setSubmitting(true);
    try {
      const group = resolveGroup();
      const created = await api.addRatio({
        numerator_stock: numerator.trim().toUpperCase(),
        denominator_stock: denominator.trim().toUpperCase(),
        group_name: group,
      });
      toast.success(
        `Added ${created.numerator}/${created.denominator} (#${created.id})`,
      );
      setNumerator("");
      setDenominator("");
      setGroupChoice(NO_GROUP);
      setNewGroupName("");
      await onSubmitted(group);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="form-stack" onSubmit={submit}>
      <div>
        <label htmlFor="numerator">Numerator</label>
        <input
          id="numerator"
          value={numerator}
          onChange={(e) => setNumerator(e.target.value)}
          placeholder="e.g. NVDA"
          required
        />
      </div>
      <div>
        <label htmlFor="denominator">Denominator</label>
        <input
          id="denominator"
          value={denominator}
          onChange={(e) => setDenominator(e.target.value)}
          placeholder="e.g. SOXX"
          required
        />
      </div>
      <div>
        <label htmlFor="group">Group</label>
        <select
          id="group"
          value={groupChoice}
          onChange={(e) => setGroupChoice(e.target.value)}
        >
          <option value={NO_GROUP}>(none)</option>
          {knownGroups.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
          <option value={NEW_GROUP}>+ New group…</option>
        </select>
        {groupChoice === NEW_GROUP && (
          <input
            style={{ marginTop: 8 }}
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
            placeholder="New group name, e.g. semiconductors"
            autoFocus
            required
          />
        )}
      </div>
      <button
        type="submit"
        disabled={
          submitting ||
          groupChoice === NO_GROUP ||
          (groupChoice === NEW_GROUP && newGroupName.trim() === "")
        }
      >
        {submitting ? "Submitting…" : "Submit"}
      </button>
    </form>
  );
}
