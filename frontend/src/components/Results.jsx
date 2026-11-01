import { useEffect, useState } from "react";
import { categoryOf, describeName } from "../categories";

const METHODS = [
  ["ours", "Night Sky Finder", "Meta's AI + our measuring tools"],
  ["video", "Meta's AI, just watching the video", "No measurements, no tools"],
  ["frames", "Meta's AI, looking at 8 photos", "8 still pictures taken from the video"],
];
const COL = { ours: 2, video: 3, frames: 4 }; // positions in each row of results.json

// right / not sure / wrong against the expert answer (meteor or not a meteor)
function grade(expert, answer) {
  if (answer === "unsure") return "unsure";
  return (expert === "meteor") === (answer === "meteor") ? "right" : "wrong";
}

function score(rows, method) {
  const c = { right: 0, unsure: 0, wrong: 0, total: 0, found: 0, calls: 0, meteors: 0 };
  rows.forEach((r) => {
    const expert = r[1];
    const a = r[COL[method]];
    if (!expert || !a) return;
    c.total++;
    c[grade(expert, a)]++;
    if (expert === "meteor") c.meteors++;
    if (a === "meteor") {
      c.calls++;
      if (expert === "meteor") c.found++;
    }
  });
  return c;
}

const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);

function Bar({ c }) {
  return (
    <div className="rbar" role="img" aria-label={`${c.right} right, ${c.unsure} not sure, ${c.wrong} wrong`}>
      {["right", "unsure", "wrong"].map((k) =>
        c[k] ? (
          <span key={k} className={`rbar__seg rbar__seg--${k}`} style={{ flex: c[k] }} title={`${c[k]} ${k === "unsure" ? "not sure" : k}`}>
            {c[k]}
          </span>
        ) : null,
      )}
    </div>
  );
}

function Answer({ value, expert }) {
  if (!value) return <span className="muted">—</span>;
  const cat = categoryOf(value);
  const g = expert ? grade(expert, value) : null;
  return (
    <span className="ans" style={{ "--c": cat.color }}>
      {cat.label}
      {g && <i className={`ans__mark ans__mark--${g}`}>{g === "right" ? "✓" : g === "wrong" ? "✗" : "?"}</i>}
    </span>
  );
}

export default function Results() {
  const [data, setData] = useState(null);
  const [groupId, setGroupId] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetch("/results.json")
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setGroupId(d.groups?.[0]?.id);
      })
      .catch(() => setData({ groups: [] }));
  }, []);
  if (!data) return null;
  const group = data.groups.find((g) => g.id === groupId);
  if (!group) return <p className="hint">No results yet. Run scripts/make_results.py.</p>;

  const s = Object.fromEntries(METHODS.map(([k]) => [k, score(group.rows, k)]));
  const ours = s.ours;
  const shown = group.rows.filter((r) => filter === "all" || (filter === "meteor" ? r[1] === "meteor" : r[1] !== "meteor"));

  return (
    <div className="results">
      <section className="block results__score">
        <div className="block__head">
          <div>
            <h2 className="cap">Does Night Sky Finder do better than the AI on its own?</h2>
            <p className="hint">Same Meta AI (Muse Spark), same clips. Each answer is checked against the known answer: meteor or not a meteor.</p>
          </div>
        </div>
        <div className="rgroups" role="tablist">
          {data.groups.map((g) => (
            <button key={g.id} role="tab" aria-selected={g.id === groupId} onClick={() => setGroupId(g.id)}>
              {g.title} · {g.rows.length} clips
            </button>
          ))}
          {data.groups.length < 2 && <span className="rgroups__soon">Named by the AllSky7 network · coming next</span>}
        </div>
        <div className="rchart">
          {METHODS.map(([key, name, how]) => (
            <div key={key} className={`rchart__row${key === "ours" ? " rchart__row--ours" : ""}`}>
              <div className="rchart__name">
                <b>{name}</b>
                <span>{how}</span>
              </div>
              <Bar c={s[key]} />
              <div className="rchart__num">
                <b>{pct(s[key].right, s[key].total)}%</b> right
              </div>
            </div>
          ))}
          <div className="rlegend">
            <span><i className="rbar__seg--right" />Right</span>
            <span><i className="rbar__seg--unsure" />Not sure</span>
            <span><i className="rbar__seg--wrong" />Wrong</span>
            <span className="muted">{group.who}</span>
          </div>
        </div>
      </section>

      <section className="block results__facts">
        <div className="fact">
          <b>{ours.found}/{ours.meteors}</b>
          <span>
            Meteors Night Sky Finder found. The AI on its own: {s.video.found} watching the video, {s.frames.found} looking at photos.
          </span>
        </div>
        <div className="fact">
          <b>{pct(ours.found, ours.calls)}%</b>
          <span>When Night Sky Finder says "meteor", it is right ({ours.found} of {ours.calls} times).</span>
        </div>
        <div className="fact">
          <b>{pct(ours.wrong, ours.total)}%</b>
          <span>Wrong answers. When it can't tell, it says "not sure" ({ours.unsure} clips) instead of guessing.</span>
        </div>
        {group.cost_per_clip && (
          <div className="fact">
            <b>~{(group.cost_per_clip * 100).toFixed(1)}¢</b>
            <span>Cost to check one clip with Meta's AI, in about 10 seconds.</span>
          </div>
        )}
        <div className="note">
          <b>Honest notes</b>
          <p>We never tuned our tool on these {group.rows.length} clips. They were picked at random, half meteors, half not.</p>
          <p>Night Sky Finder gives the AI exact numbers, like how long the object was visible. That helps a lot, and it is exactly what our tools are for.</p>
        </div>
      </section>

      <section className="block results__table">
        <div className="block__head">
          <h2 className="cap">All {group.rows.length} clips</h2>
          <div className="rfilter">
            {[["all", "All"], ["meteor", "Meteors"], ["not", "Not meteors"]].map(([k, label]) => (
              <button key={k} aria-pressed={filter === k} onClick={() => setFilter(k)}>{label}</button>
            ))}
            <span className="hint">✓ right · ✗ wrong · ? not sure · tested {data.tested}</span>
          </div>
        </div>
        <div className="rtable">
          <table>
            <thead>
              <tr>
                <th>Clip</th>
                <th>Known answer</th>
                <th>Night Sky Finder</th>
                <th>AI watching the video</th>
                <th>AI looking at 8 photos</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => {
                const info = describeName(r[0]);
                return (
                  <tr key={r[0]}>
                    <td>{group.id === "allsky7" ? "AllSky7 network" : info.place}<span className="muted">{info.when ? ` · ${info.when}` : ""}</span></td>
                    <td>{r[1] === "meteor" ? "Meteor" : r[1] ? "Not a meteor" : "—"}</td>
                    <td><Answer value={r[2]} expert={r[1]} /></td>
                    <td><Answer value={r[3]} expert={r[1]} /></td>
                    <td><Answer value={r[4]} expert={r[1]} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
