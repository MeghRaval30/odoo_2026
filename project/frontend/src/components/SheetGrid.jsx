// The spreadsheet, drawn as it arrived and then coloured as it is understood.
//
// This component is the reason the feature is convincing. An import that
// reports "22 rows mapped" asks to be believed; one that shows you your own
// file with the header row it found highlighted, the two title rows above it
// struck through, and each column tinted the colour of the field it became,
// has already answered the question.
//
// So it renders the raw rows too, not just the parsed ones. The junk above the
// header is the evidence that header detection did something.

import { FieldChip, ScanBeam, hueVar, hueWash } from "./ai";

const NUMERIC = new Set(["wage", "bank_account_number", "work_phone",
                         "personal_phone", "employee_code"]);

export default function SheetGrid({
  headers = [],
  rows = [],
  rawRows = [],
  headerRowIndex = 0,
  junkIdentified = false,
  columnState = {},
  onHeaderClick,
  scanning = false,
  maxRows = 14,
  fields = [],
}) {
  const junk = rawRows.slice(0, headerRowIndex);
  const width = headers.length;
  const labelFor = (key) =>
    fields.find((f) => f.key === key)?.label || key;

  return (
    <div className="sheet-wrap">
      <ScanBeam active={scanning} />
      <table className="sheet">
        <thead>
          <tr>
            <th className="rownum" />
            {headers.map((h, i) => {
              const state = columnState[i] || {};
              const mapped = Boolean(state.field);
              return (
                <th
                  key={i}
                  className={`${onHeaderClick ? "clickable " : ""}${
                    state.pulsing ? "pulsing " : ""
                  }${state.decided && !mapped ? "unmapped" : ""}`}
                  style={
                    mapped
                      ? {
                          background: hueWash(state.hue),
                          borderBottom: `2px solid ${hueVar(state.hue)}`,
                        }
                      : undefined
                  }
                  onClick={() => onHeaderClick?.(i)}
                  title={onHeaderClick ? "Change what this column maps to" : h}
                >
                  <span className="sheet-head-label">{h}</span>
                  {mapped ? (
                    <FieldChip label={labelFor(state.field)} hue={state.hue} />
                  ) : state.decided ? (
                    <span className="tiny faint">not imported</span>
                  ) : (
                    <span className="tiny faint">&nbsp;</span>
                  )}
                </th>
              );
            })}
          </tr>
        </thead>

        <tbody>
          {/* Everything above the detected header, kept visible on purpose. */}
          {junk.map((row, r) => (
            <tr key={`junk-${r}`} className={`junk${junkIdentified ? " identified" : ""}`}>
              <td className="rownum">{r + 1}</td>
              <td colSpan={width}>
                {(row || []).filter(Boolean).join("  ") || <em>(blank row)</em>}
              </td>
            </tr>
          ))}

          {rawRows[headerRowIndex] && (
            <tr className="headerline">
              <td className="rownum">{headerRowIndex + 1}</td>
              <td colSpan={width}>
                {junkIdentified
                  ? `Header row — ${width} columns`
                  : (rawRows[headerRowIndex] || []).filter(Boolean).join("  ")}
              </td>
            </tr>
          )}

          {rows.slice(0, maxRows).map((row, r) => (
            <tr key={r}>
              <td className="rownum">{headerRowIndex + 2 + r}</td>
              {headers.map((_, i) => {
                const state = columnState[i] || {};
                const mapped = Boolean(state.field);
                return (
                  <td
                    key={i}
                    className={`${state.pulsing ? "pulsing " : ""}${
                      state.decided && !mapped ? "unmapped " : ""
                    }${NUMERIC.has(state.field) ? "mono" : ""}`}
                    style={mapped ? { background: hueWash(state.hue) } : undefined}
                    title={row[i]}
                  >
                    {row[i] || <span className="faint">&mdash;</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {rows.length > maxRows && (
        <div className="tiny faint" style={{ padding: "6px 10px" }}>
          Showing {maxRows} of {rows.length} rows. Every row is imported.
        </div>
      )}
    </div>
  );
}
