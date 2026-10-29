const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options) {
  const res = await fetch(BASE + path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const getHealth = () => request("/api/health");
export const getSamples = () => request("/api/samples");

export const analyzeSample = (name) =>
  request(`/api/samples/analyze?name=${encodeURIComponent(name)}`, { method: "POST" });

export const analyzeUpload = (file) => {
  const form = new FormData();
  form.append("file", file);
  return request("/api/analyze", { method: "POST", body: form });
};

export const sampleFileUrl = (name) =>
  `${BASE}/api/samples/file?name=${encodeURIComponent(name)}`;

export const measureSample = (name) =>
  request(`/api/samples/measure?name=${encodeURIComponent(name)}`, { method: "POST" });

export const investigateSample = (name) =>
  request(`/api/samples/investigate?name=${encodeURIComponent(name)}`, { method: "POST" });

export const classifySample = (name) =>
  request(`/api/samples/classify?name=${encodeURIComponent(name)}`, { method: "POST" });
