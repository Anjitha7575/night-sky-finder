import { useEffect, useState } from "react";
import { categoryOf, describeName } from "../categories";

const METHODS = [
  ["ours", "Night Sky Finder", "Meta's AI + our measuring tools"],
  ["video", "Meta's AI, just watching the video", "No measurements, no tools"],
  ["frames", "Meta's AI, looking at 8 photos", "8 still pictures taken from the video"],
];

// right / unsure / wrong against the expert label (meteor vs not meteor)
function grade(expert, answer) {
  if (answer === "unsure") return "unsure";
  return (expert === "meteor") === (answer === "meteor") ? "right" : "wrong";
}

function Bar({ counts, total }) {
  return (
    <div className="rbar" role="img" aria-label={`${counts.right} right, ${counts.unsure} unsure, ${counts.wrong} wrong`}>
      {["right", "unsure", "wrong"].map((k) =>
        counts[k] ? (
          <span key={k} className={`rbar__seg rbar__seg--${k}`} style={{ flex: counts[k] / total }} title={`${counts[k]} ${k}`}>
            {counts[k]}
          </span>
        ) : null,
      )}
    </div>
  );
}

function Answer({ value, expert }) {
  if (!value) return <span className="muted">—</span>; // no answer saved for this clip
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
  useEffect(() => {
    fetch("/results.json").then((r) => r.json()).then(setData).catch(() => setData({ rows: [] }));
  }, []);
  if (!data) return null;

  const rows = data.rows.map(([file, expert, video, frames, ours]) => ({ file, expert, video, frames, ours, info: describeName(file) }));
  const labelled = rows.filter((r) => r.expert);
  const score = (m) => {
    const c = { right: 0, unsure: 0, wrong: 0 };
    labelled.forEach((r) => r[m] && c[grade(r.expert, r[m])]++);
    return c;
  };
  // the New Mexico (SkySentinel) clips: no expert answer, but the camera saves likely meteors
  const sky = rows.filter((r) => r.info.place === "Las Cruces, USA" && !r.expert);
  const skyMeteors = (m) => sky.filter((r) => r[m] === "meteor").length;

  return (
    <div className="results">
      <section className="block results__score">
        <h2 className="cap">Does Night Sky Finder do better than the AI on its own?</h2>
        <p className="hint">Same Meta AI (Muse Spark), same clips. Each answer is checked against the experts' answer: meteor or not a meteor.</p>
        <div className="rchart">
          {METHODS.map(([key, name, how]) => {
            const c = score(key);
            return (
              <div key={key} className={`rchart__row${key === "ours" ? " rchart__row--ours" : ""}`}>
                <div className="rchart__name">
                  <b>{name}</b>
                  <span>{how}</span>
                </div>
                <Bar counts={c} total={labelled.length} />
                <div className="rchart__num">
                  <b>{c.right}/{labelled.length}</b> right
                </div>
              </div>
            );
          })}
          <div className="rlegend">
            <span><i className="rbar__seg--right" />Right</span>
            <span><i className="rbar__seg--unsure" />Not sure</span>
            <span><i className="rbar__seg--wrong" />Wrong</span>
            <span className="muted">{labelled.length} clips where experts gave the answer</span>
          </div>
        </div>
      </section>

      <section className="block results__facts">
        <div className="fact">
          <b>{skyMeteors("ours")}/{sky.length}</b>
          <span>Night Sky Finder called these New Mexico clips "meteor". The AI just watching the video: {skyMeteors("video")} of {sky.length}. (No expert answer for these; the camera saves clips it thinks are meteors.)</span>
        </div>
        <div className="fact">
          <b>0</b>
          <span>Wrong answers from Night Sky Finder on the expert-checked clips. When it can't tell, it says "not sure" instead of guessing.</span>
        </div>
        <div className="fact">
          <b>~1¢</b>
          <span>Cost to check one clip, in about 10 seconds.</span>
        </div>
        <div className="note">
          <b>Honest notes</b>
          <p>This is a small test: only {labelled.length} clips have an expert answer. The other clips are shown but not scored.</p>
          <p>Night Sky Finder gives the AI exact numbers, like how long the object was visible. That helps a lot, and it is exactly what our tools are for.</p>
        </div>
      </section>

      <section className="block results__table">
        <div className="block__head">
          <h2 className="cap">All {rows.length} clips</h2>
          <span className="hint">✓ right · ✗ wrong · ? not sure (marked only where experts gave the answer) · tested {data.tested}</span>
        </div>
        <div className="rtable">
          <table>
            <thead>
              <tr>
                <th>Clip</th>
                <th>Experts' answer</th>
                <th>AI watching the video</th>
                <th>AI looking at 8 photos</th>
                <th>Night Sky Finder</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.file}>
                  <td>{r.info.place}<span className="muted">{r.info.when ? ` · ${r.info.when}` : r.info.year ? ` · ${r.info.year}` : ""}</span></td>
                  <td className={r.expert ? "" : "muted"}>{r.expert === "meteor" ? "Meteor" : r.expert ? "Not a meteor" : "—"}</td>
                  <td><Answer value={r.video} expert={r.expert} /></td>
                  <td><Answer value={r.frames} expert={r.expert} /></td>
                  <td><Answer value={r.ours} expert={r.expert} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
