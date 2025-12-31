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

