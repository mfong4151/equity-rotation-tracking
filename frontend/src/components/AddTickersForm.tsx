import { useState } from "react";
import { toast } from "sonner";
import { api } from "../api/client";

interface Props {
  onAdded: (added: string[]) => void | Promise<void>;
}

const emptyRow = () => ({ id: Math.random().toString(36).slice(2), value: "" });

export default function AddTickersForm({ onAdded }: Props) {
  const [rows, setRows] = useState([emptyRow(), emptyRow()]);
  const [submitting, setSubmitting] = useState(false);

  const updateRow = (id: string, value: string) =>
    setRows((cur) => cur.map((r) => (r.id === id ? { ...r, value } : r)));

  const addRow = () => setRows((cur) => [...cur, emptyRow()]);

  const removeRow = (id: string) =>
    setRows((cur) => (cur.length > 1 ? cur.filter((r) => r.id !== id) : cur));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const symbols = Array.from(
      new Set(rows.map((r) => r.value.trim().toUpperCase()).filter(Boolean)),
    );
    if (symbols.length === 0) {
      toast.error("Add at least one ticker symbol");
      return;
    }
    setSubmitting(true);
    const dismiss = toast.loading(`Adding ${symbols.length} ticker(s)…`);
    try {
      const resp = await api.addTickersBatch(symbols);
      toast.dismiss(dismiss);
      const ok = resp.results.filter((r) => r.ok);
      const bad = resp.results.filter((r) => !r.ok);
      if (ok.length) toast.success(`Added ${ok.map((r) => r.ticker_symbol).join(", ")}`);
      bad.forEach((r) => toast.error(`${r.ticker_symbol}: ${r.error ?? "failed"}`));
      if (ok.length) {
        setRows([emptyRow(), emptyRow()]);
        await onAdded(ok.map((r) => r.ticker_symbol));
      }
    } catch (err) {
      toast.dismiss(dismiss);
      toast.error((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="form-stack" onSubmit={submit}>
      {rows.map((row, idx) => (
        <div key={row.id} className="ticker-row">
          <input
            value={row.value}
            onChange={(e) => updateRow(row.id, e.target.value)}
            placeholder={idx === 0 ? "e.g. NVDA" : "e.g. AMD"}
            aria-label={`Ticker ${idx + 1}`}
          />
          <button
            type="button"
            className="icon remove"
            onClick={() => removeRow(row.id)}
            disabled={rows.length <= 1}
            title="Remove row"
            aria-label="Remove row"
          >
            −
          </button>
        </div>
      ))}
      <button type="button" className="add-row" onClick={addRow}>
        + add another
      </button>
      <button type="submit" disabled={submitting}>
        {submitting ? "Submitting…" : "Submit tickers"}
      </button>
    </form>
  );
}
