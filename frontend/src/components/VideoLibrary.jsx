import { useEffect, useRef, useState } from "react";
import { sampleFileUrl } from "../api";
import { Play, Upload } from "./Icons";

const fmt = (sec) => {
  if (sec == null || !isFinite(sec)) return null;
  const s = Math.round(sec);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};

export function srcOf(item) {
  return item.upload ? item.objectUrl : sampleFileUrl(item.name);
}
export const isVideo = (name) => /\.(mp4|webm|mov|avi)$/i.test(name);

function Card({ item, newest, on, onSelect }) {
  const [duration, setDuration] = useState(null);
  const cam = item.measured?.measured?.camera;
  const measuredDur = cam?.fps ? cam.frames / cam.fps : null;
  const shown = fmt(duration ?? measuredDur);
  const src = srcOf(item);

  return (
    <button className={`vcard${on ? " vcard--on" : ""}`} data-id={item.id} onClick={() => onSelect(item.id)}>
      <span className="vcard__pic">
        {isVideo(item.name) ? (
          <video src={`${src}#t=0.5`} muted preload="metadata" onLoadedMetadata={(e) => setDuration(e.target.duration)} />
        ) : (
          <img src={src} alt="" />
        )}
      </span>
      <span className="vcard__info">
        <span className="vcard__play"><Play /></span>
        <span className="vcard__text">
          <span className="vcard__title">
            {item.upload ? "Your upload" : item.info.place}
          </span>
          <span className="vcard__sub">
            {newest && <em className="tag">Newest</em>}
            {[item.info.year, shown || (isVideo(item.name) ? null : "GIF")].filter(Boolean).join(" · ")}
          </span>
        </span>
      </span>
    </button>
  );
}

// fixed tile on the left: always visible, never scrolls away
function UploadTile({ onUpload }) {
  return (
    <button className="uptile" onClick={onUpload} title="MP4, GIF or photo, up to 50 MB">
      <span className="uptile__icon"><Upload /></span>
      <b>Check your<br />own video</b>
    </button>
  );
}

export default function VideoLibrary({ items, selected, onSelect, onUpload, tools }) {
  // the newest recording gets the "Newest" tag, wherever it sits in the list
  const newestId = items
    .filter((i) => !i.upload && i.info.sortKey)
    .reduce((best, i) => (!best || i.info.sortKey > best.info.sortKey ? i : best), null)?.id;
  const track = useRef(null);
  const [edge, setEdge] = useState({ start: true, end: false });

  function onScroll() {
    const el = track.current;
    if (!el) return;
    setEdge({ start: el.scrollLeft < 4, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 4 });
  }
  useEffect(onScroll, [items.length]);

  // bring the selected card into view (e.g. a new upload is added at the start)
  useEffect(() => {
    const el = track.current;
    const card = el?.querySelector(`[data-id="${CSS.escape(String(selected))}"]`);
    if (!el || !card) return;
    const left = card.offsetLeft - el.offsetLeft;
    const right = left + card.offsetWidth;
    if (left < el.scrollLeft || right > el.scrollLeft + el.clientWidth) {
      el.scrollTo({ left: Math.max(0, left - 4), behavior: "smooth" });
    }
  }, [selected, items.length]);

  // move by one "page" of cards
  const slide = (dir) => track.current?.scrollBy({ left: dir * track.current.clientWidth * 0.9, behavior: "smooth" });
  return (
    <section className="block">
      <div className="block__head">
        <div>
          <h2 className="cap">Available sky videos</h2>
          <p className="hint">Select a recording to analyze · sorted by capture date</p>
        </div>
        <div className="tools">{tools}</div>
      </div>
      <div className="library">
        <UploadTile onUpload={onUpload} />
      <div className="carousel">
        <button className="carousel__btn carousel__btn--prev" onClick={() => slide(-1)} disabled={edge.start} aria-label="Previous videos">‹</button>
        <div className="vlist" ref={track} onScroll={onScroll}>
          {items.map((item) => (
            <Card key={item.id} item={item} newest={item.id === newestId} on={item.id === selected} onSelect={onSelect} />
          ))}
        </div>
        <button className="carousel__btn carousel__btn--next" onClick={() => slide(1)} disabled={edge.end} aria-label="More videos">›</button>
      </div>
      </div>
    </section>
  );
}
