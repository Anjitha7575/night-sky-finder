import { categoryOf } from "../categories";
import { Brain, Streak } from "./Icons";

const STEPS = [
  ["measuring", "Measuring the moving object"],
  ["thinking", "Muse Spark is investigating"],
  ["done", "Answer ready"],
];
const ORDER = { idle: -1, measuring: 0, thinking: 1, done: 2, error: 2 };
const LEVEL = { low: 1, medium: 2, high: 3 };

function Steps({ status, source }) {
  const now = ORDER[status] ?? -1;
  return (
    <ol className="steps">
      {STEPS.map(([key, label], i) => {
        const state = i < now || status === "done" ? "done" : i === now ? "now" : "next";
        const text = key === "thinking" && source === "mock" ? "Simple rules are deciding (test mode)" : label;
        return <li key={key} className={`step step--${state}`}>{text}</li>;
      })}
    </ol>
  );
}

function Confidence({ level }) {
  const n = LEVEL[level] || 0;
  return (
    <span className="conf" aria-label={`Confidence: ${level}`}>
      <span className="conf__bars" aria-hidden="true">
        {[1, 2, 3].map((i) => <i key={i} className={i <= n ? "on" : ""} />)}
      </span>
      {level} confidence
    </span>
  );
}

// one row per check the AI made: picture, what it wanted to know, what it found
function Investigation({ steps }) {
  return (
    <ol className="probe">
      {steps.map((s, i) => (
        <li key={i} className="probe__step" style={{ animationDelay: `${i * 0.25}s` }}>
          <span className="probe__num">{i + 1}</span>
          <span className="probe__pic">
            {s.image_png_base64 && <img src={`data:image/png;base64,${s.image_png_base64}`} alt={s.title} />}
          </span>
          <span className="probe__text">
            <b>{s.title}</b>
            {i > 0 && s.why && <i>“{s.why}”</i>}
            {i > 0 && <span>{s.found}</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}

function measuredLine(m) {
  const parts = [];
  if (m.speed_pct_per_sec != null) parts.push(`${m.speed_pct_per_sec}% screen/s`);
  if (m.straightness != null) parts.push(`straightness ${Number(m.straightness).toFixed(2)}`);
  if (m.visible_sec != null) parts.push(`${m.visible_sec} s visible`);
  if (m.blink) parts.push(m.blink.blinking ? "blinking" : "no blinking");
  parts.push(m.flash_frames?.length ? "sky flash" : "no sky flash");
  return parts.join(" · ");
}

export default function EventPanel({ item, index, aiMode, onRetry }) {
  if (!item) return <aside className="block event" />;
  const info = item.info;
  const m = item.measured?.measured;
  const v = item.verdict;
  const steps = item.steps || [];
  const cat = v ? categoryOf(v.category) : null;
  const image = item.measured?.image_png_base64;
  const agrees = v && info.expert && (info.expert === "meteor") === (v.category === "meteor");
  const isMeta = (v?.source || aiMode) === "meta";

  return (
    <aside className="block event" style={{ "--accent": cat ? cat.color : "var(--line)" }}>
      {/* glows once each time a new answer arrives */}
      {v && <span className="event__flash" key={`${item.id}-${v.category}`} aria-hidden="true" />}
      <div className="event__head">
        <h2 className="cap">AI result · Video #{index + 1}</h2>
        <span className={`chip${isMeta ? " chip--ai" : ""}`}>{isMeta ? "Meta Muse Spark" : "Test mode: simple rules"}</span>
      </div>

      {!v && (
        <div className="event__top">
          <div className="event__shot">
            {image ? <img src={`data:image/png;base64,${image}`} alt="All frames stacked with the still sky removed" /> : <span className="event__wait" />}
            <span className="event__shotlabel">What the AI sees</span>
          </div>
          <div className="event__verdict">
            {item.status !== "error" && <Steps status={item.status} source={isMeta ? "meta" : "mock"} />}
            {item.status === "error" && (
              <p className="err">
                {item.error} <button className="link" onClick={onRetry}>Try again</button>
              </p>
            )}
          </div>
        </div>
      )}

      {v && (
        <>
          <div className="event__verdict event__verdict--wide">
            <span className="verdict__icon"><Streak /></span>
            <div>
              <b className="verdict__name">
                {v.category === "unsure" ? "Not sure" : v.confidence === "low" ? `Maybe ${cat.label}` : `Likely ${cat.label}`}
              </b>
              <Confidence level={v.confidence} />
              <span className="verdict__meta">
                Decided after {steps.length} {steps.length === 1 ? "look" : "checks"}
                {v.key_clue ? ` · key clue: ${v.key_clue}` : ""}
              </span>
            </div>
          </div>

          <div className="explain">
            <h3><Brain /> Why the AI thinks so</h3>
            <p className="explain__reason">{v.reason}</p>
            {v.next_step !== "none" && (
              <p className="explain__next">
                {v.next_step === "watch_video" ? "Worth watching the clip to be sure." : "Needs a human check."}
              </p>
            )}
            {info.expert && (
              <p className={`explain__expert ${agrees ? "good" : "bad"}`}>
                Experts say: {info.expert}. {agrees ? "The AI agrees ✓" : "The AI got this one wrong."}
              </p>
            )}
          </div>

          {steps.length > 0 && (
            <>
              <h3 className="cap cap--small">How the AI checked</h3>
              <Investigation steps={steps} />
            </>
          )}

          {m && <p className="measured"><b>Measured by our code:</b> {measuredLine(m)}</p>}
        </>
      )}
    </aside>
  );
}
