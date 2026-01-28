// 公共配置（会随 GitHub Pages 一起发布）
// 注意：不要在这里放任何 secret（API Key / Token）。这里只放公开信息，例如 Cloud Run URL。
window.LOCAL_CONFIG = {
  // 默认优先走自建/云端聊天服务（Cloud Run）
  AI_PROVIDER: "adk",
  ADK_CHAT_URL: "https://my-agent-api-531513049365.us-central1.run.app/api/chat",
  ADK_PROVIDER: "vertex",
  ADK_MODEL: "gemini-2.5-flash",
};


