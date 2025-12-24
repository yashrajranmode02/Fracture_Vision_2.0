const API_BASE = "http://localhost:8000";

export async function uploadXray(file) {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(`${API_BASE}/upload/xray`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) throw new Error("X-ray upload failed");
  return res.json();
}

export async function uploadModel(file, sessionId) {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(
    `${API_BASE}/upload/model?session_id=${sessionId}`,
    { method: "POST", body: fd }
  );

  if (!res.ok) throw new Error("Model upload failed");
}

export async function processLandmarks(sessionId, landmarks) {
  const res = await fetch(`${API_BASE}/process/landmarks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, landmarks }),
  });

  if (!res.ok) throw new Error("Processing failed");
  return res.json();
}

export function getModelUrl(sessionId) {
  return `${API_BASE}/model/${sessionId}/original?t=${Date.now()}`;
}
