# HK 3DGS Explorer | 香港 3D 高斯泼溅地图

基于地理位置的分布式 3D 场景重建与展示平台。

## 架构

- **前端 (Web)**: 基于 Three.js + geo-three 的全港 3D 地图，负责展示、交互和任务提交。
- **云端 (Hugging Face)**: 存储 dataset (`locations.json` 和图片/模型数据)，充当消息总线。
- **本地计算节点 (Local GPU)**: 监听云端任务，执行 3DGS 重建，回传结果。

## 快速开始

### 1. 前端启动
直接在浏览器打开 `index.html` (需通过本地服务器，如 Live Server)。
或者使用 Python 启动简单服务器：
```bash
python -m http.server 8000
```
访问: `http://localhost:8000`

### 1.5（可选）使用 Vertex AI 作为 AI 聊天后端（推荐）

> 原因：Vertex AI 需要 GCP 身份认证（OAuth/Service Account），**不应把凭据放进前端**。推荐做法是用一个本地/云端代理服务，由代理去调用 Vertex AI，再把结果返回给前端。

#### A) 启动本地 Vertex AI 代理（FastAPI）

安装依赖：
```bash
pip install -r requirements.txt
```

配置 GCP（任选一种）：
- **本机开发**：安装并登录 gcloud，然后：
```bash
gcloud auth application-default login
```
- 或者使用 **Service Account**（更适合部署到 Cloud Run/服务器）：设置 `GOOGLE_APPLICATION_CREDENTIALS` 指向 json。

设置项目/区域（PowerShell 示例）：
```powershell
$env:VERTEX_PROJECT_ID="你的GCP项目ID"
$env:VERTEX_LOCATION="us-central1"
$env:VERTEX_MODEL="gemini-2.5-flash"
```

启动代理（默认端口 8787）：
```bash
uvicorn vertex_ai_proxy:app --host 0.0.0.0 --port 8787
```

然后在 `config.local.js` 里加上（本地私密配置）：
```js
window.LOCAL_CONFIG = {
  AI_PROVIDER: "vertex",
  VERTEX_PROXY_URL: "http://localhost:8787/api/vertex/generate",
  VERTEX_MODEL: "gemini-2.5-flash",
};
```

#### B) 部署到 Cloud Run（简述）
- 把 `vertex_ai_proxy.py` 容器化并部署到 Cloud Run
- 给 Cloud Run 服务绑定有 Vertex AI 调用权限的 Service Account
- 前端把 `VERTEX_PROXY_URL` 换成你的 Cloud Run HTTPS 地址

### 2. 启动本地计算节点
本地节点负责处理上传的照片并生成 3D 模型。

**依赖安装:**
```bash
pip install huggingface_hub
```

**配置 Token:**
你需要一个 Hugging Face Write 权限的 Token。
PowerShell:
```powershell
$env:HF_TOKEN="你的HF_TOKEN"
```

**运行:**
```bash
python process_server.py
```

## 功能说明

1. **地图交互**: 浏览香港地图，点击任意位置拾取坐标。
2. **提交任务**: 上传照片，填写描述，提交后状态为 "Processing"。
3. **自动处理**: `process_server.py` 监听到新任务，调用本地 `ml-sharp` 执行 3D 重建。
4. **查看模型**: 任务完成后，前端变为 "Ready"，点击进入 3D 沉浸式查看。

## 开发注记

- **依赖**: 本地环境需安装并配置好 `sharp` 命令行工具 (来自 [apple/ml-sharp](https://github.com/apple/ml-sharp))。
- **流程**: 脚本会自动下载图片 -> 运行 `sharp predict` -> 上传生成的 `.ply` 模型。

