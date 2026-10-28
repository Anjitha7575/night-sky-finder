import { useEffect, useState } from "react";
import { getHealth, getSamples, analyzeSample } from "./api";

export default function App() {
  const [health, setHealth] = useState(null);
  const [samples, setSamples] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getHealth().then(setHealth).catch((e) => setError(e.message));
    getSamples().then(setSamples).catch((e) => setError(e.message));
  }, []);

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>Night Sky Finder</h1>
      <p>Backend: {health ? `${health.status} (AI: ${health.ai_mode})` : "…"}</p>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <ul>
        {samples.map((s) => (
          <li key={s}>
            <button onClick={() => analyzeSample(s).then(setResult).catch((e) => setError(e.message))}>
              {s}
            </button>
          </li>
        ))}
      </ul>

      {result && (
        <section>
          <img src={`data:image/png;base64,${result.image_png_base64}`} width={320} />
          <h2>{result.verdict.category} ({result.verdict.confidence})</h2>
          <p>{result.verdict.reason}</p>
          <pre>{JSON.stringify(result.measured, null, 2)}</pre>
        </section>
      )}
    </main>
  );
}