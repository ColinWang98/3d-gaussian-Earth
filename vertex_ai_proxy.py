import os
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GoogleAuthRequest


app = FastAPI(title="Vertex AI Proxy", version="0.1.0")

# 本地开发方便：允许浏览器直连这个代理（生产环境请收紧 allow_origins）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


def _get_access_token() -> str:
    credentials, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise RuntimeError("Failed to get Google access token (ADC not configured).")
    return credentials.token


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/vertex/generate")
def vertex_generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    前端请求格式（最小）：
      {
        "text": "...",
        "system": "...",
        "image": { "mimeType": "image/jpeg", "data": "<base64>" }  // 可选
        "model": "gemini-2.5-flash" // 可选
      }

    说明：
    - Vertex AI 使用 GCP 身份认证（ADC），不要把 Service Account 放到前端。
    - 模型与 API 版本以 Vertex AI 文档为准。
    """
    project = os.environ.get("VERTEX_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("VERTEX_LOCATION", "us-central1")
    model = (payload.get("model") or os.environ.get("VERTEX_MODEL") or "gemini-2.5-flash").strip()

    if not project:
        raise HTTPException(
            status_code=500,
            detail="Missing VERTEX_PROJECT_ID (or GOOGLE_CLOUD_PROJECT).",
        )

    text: str = (payload.get("text") or "").strip()
    system: str = (payload.get("system") or "").strip()
    image: Optional[Dict[str, str]] = payload.get("image")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text.")

    parts = []
    if system:
        parts.append({"text": system})
    if image and image.get("data") and image.get("mimeType"):
        parts.append({"inlineData": {"mimeType": image["mimeType"], "data": image["data"]}})
    parts.append({"text": text})

    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/"
        f"projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent"
    )
    try:
        token = _get_access_token()
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"role": "user", "parts": parts}],
            },
            timeout=60,
        )
        data = res.json() if res.content else {}
        if not res.ok:
            raise HTTPException(status_code=res.status_code, detail=data)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


