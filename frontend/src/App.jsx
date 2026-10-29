import { useEffect, useRef, useState } from "react";
import { analyzeUpload, getHealth, getSamples, investigateSample, measureSample } from "./api";
import { describeName } from "./categories";
import { Info, Planet } from "./components/Icons";
import VideoLibrary from "./components/VideoLibrary";
import Player from "./components/Player";
import EventPanel from "./components/EventPanel";
import Timeline from "./components/Timeline";
import HowItWorks from "./components/HowItWorks";

const newestFirst = (a, b) => (b.info.sortKey || "").localeCompare(a.info.sortKey || "");

export default function App() {
  const [health, setHealth] = useState(null);
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showHow, setShowHow] = useState(true);
  const [error, setError] = useState("");
  const fileInput = useRef(null);

  const update = (id, patch) =>
    setItems((list) => list.map((i) => (i.id === id ? { ...i, ...patch } : i)));

  async function run(item) {
    try {
      update(item.id, { status: "measuring", error: null });
      const measured = await measureSample(item.name);
      update(item.id, { status: "thinking", measured });
      const { verdict, steps } = await investigateSample(item.name);
      update(item.id, { status: "done", verdict, steps });
    } catch (e) {
      update(item.id, { status: "error", error: e.message });
    }
  }

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ status: "down" }));
    getSamples()
      .then((names) => {
        const list = names
          .map((name) => ({ id: name, name, info: describeName(name), status: "idle" }))
          .sort(newestFirst);
        setItems(list);
        if (list.length) {
          setSelected(list[0].id);
          run(list[0]);
        }
      })
      .catch(() => setError("Can't reach the backend. Start it with uvicorn, then refresh."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function select(id) {
    setSelected(id);
    const item = items.find((i) => i.id === id);
    if (item && item.status === "idle") run(item);
  }

  async function checkAll() {
    setBusy(true);
    for (const item of items.filter((i) => i.status === "idle")) {
      await run(item); // one at a time, so the AI is not flooded
    }
    setBusy(false);
  }

  async function upload(file) {
    if (!file) return;
    const id = `upload-${Date.now()}`;
    const objectUrl = URL.createObjectURL(file);
    const info = describeName(file.name);
    setItems((list) => [{ id, name: file.name, info, upload: true, objectUrl, status: "measuring" }, ...list]);
    setSelected(id);
    try {
      const r = await analyzeUpload(file);
      update(id, {
        status: "done",
        verdict: r.verdict,
        steps: r.steps,
        measured: { measured: r.measured, image_png_base64: r.image_png_base64, preview_png_base64: r.preview_png_base64 },
      });
    } catch (e) {
      update(id, { status: "error", error: e.message });
    }
  }

  const index = items.findIndex((i) => i.id === selected);
  const current = items[index];
  const isMeta = health?.ai_mode === "meta";

  return (
    <div className="page">
      <div className="scene" aria-hidden="true" />

      <header className="top">
        <div className="brand">
          <span className="brand__logo"><Planet /></span>
          <div>
            <h1>Night Sky Finder</h1>
            <p>Let AI check your sky camera clips</p>
          </div>
        </div>
        <div className="top__right">
          <p className="tagline">
            Automatically filters hundreds of sky clips
            <br />
            and tells you which few are worth a look.
          </p>
          <button className="infobtn" onClick={() => setShowHow((v) => !v)} aria-expanded={showHow}>
            <Info />
            How it works
          </button>
        </div>
      </header>

      <section className="intro">
        <p>
          Sky cameras capture anything that moves. Night Sky Finder measures each clip and uses AI to identify
          meteors, planes, satellites and clouds, so owners don't have to review hundreds by hand.
        </p>
      </section>

      <div className="app">
        {showHow && <HowItWorks />}

        <VideoLibrary
          items={items}
          selected={selected}
          onSelect={select}
          tools={
            <>
              <span className={`mode${isMeta ? " mode--live" : ""}`}>
                {health?.status === "down" ? "Backend offline" : isMeta ? "AI: Meta Muse Spark" : "Test mode: simple rules"}
              </span>
              <button className="ghost" onClick={() => fileInput.current?.click()}>+ Check your own video</button>
              <input
                ref={fileInput}
                type="file"
                accept="video/*,image/*,.gif"
                hidden
                onChange={(e) => {
                  upload(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </>
          }
        />

        {error && <p className="err">{error}</p>}

        <div className="work">
          <div className="work__left">
            <Player item={current} />
            <Timeline items={items} selected={selected} onSelect={select} onCheckAll={checkAll} busy={busy} />
          </div>
          <EventPanel item={current} index={index} aiMode={health?.ai_mode} onRetry={() => current && run(current)} />
        </div>

        <footer className="foot">
          Videos: NightSkyUCP (CC BY-NC-SA 4.0), IAC all-sky meteors 2016 (CC BY 4.0). Background picture made with ChatGPT.
          Built for the Meta Global AI Developer Hackathon.
        </footer>
      </div>
    </div>
  );
}
