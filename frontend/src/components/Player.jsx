import { isVideo, srcOf } from "./VideoLibrary";

export default function Player({ item }) {
  if (!item) return <section className="block player" />;
  const src = srcOf(item);
  return (
    <section className="block player">
      <h2 className="cap">
        Selected recording
        <span className="cap__sub">
          {item.upload ? "Your upload" : [item.info.when || item.info.year, item.info.place].filter(Boolean).join(" · ")}
        </span>
      </h2>
      <div className="player__screen">
        {isVideo(item.name) ? (
          <video key={src} src={src} autoPlay loop muted playsInline controls />
        ) : (
          <img key={src} src={src} alt="Sky camera recording" />
        )}
      </div>
    </section>
  );
}
