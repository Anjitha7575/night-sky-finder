import { categoryOf } from "../categories";

export default function Timeline({ items, selected, onSelect, onCheckAll, busy }) {
  const checked = items.filter((i) => i.verdict);
  const left = items.filter((i) => i.status === "idle").length;
  return (
    <section className="block">
      <div className="block__head">
        <h2 className="cap">
          Event timeline <span className="cap__sub">(what the AI found so far)</span>
        </h2>
        {left > 0 && (
          <button className="ghost" onClick={onCheckAll} disabled={busy}>
            Check all {left} left
          </button>
        )}
      </div>
      {checked.length === 0 ? (
        <p className="hint">Nothing checked yet.</p>
      ) : (
        <ul className="tl">
          {checked.map((item) => {
            const cat = categoryOf(item.verdict.category);
            const pic = item.measured?.preview_png_base64;
            return (
              <li key={item.id}>
                <button className={`tl__item${item.id === selected ? " tl__item--on" : ""}`} onClick={() => onSelect(item.id)} style={{ "--c": cat.color }}>
                  <span className="tl__pic">{pic && <img src={`data:image/png;base64,${pic}`} alt="" />}</span>
                  <span className="tl__time">{item.upload ? "Upload" : (item.info.when || "").split(",")[0] || item.info.year || "Clip"}</span>
                  <span className="tl__label">{cat.short || cat.label}</span>
                  {item.steps?.length > 1 && <span className="tl__checks">{item.steps.length} checks</span>}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
