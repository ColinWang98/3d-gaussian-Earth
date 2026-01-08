import time
import json
import os
import sys
import shutil
import subprocess
import glob
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import RepositoryNotFoundError


# 配置
REPO_ID = "ColinWong24/my-gaussian-world"
REPO_TYPE = "dataset"
LOCAL_DIR = "./local_cache"
POLL_INTERVAL = 5  # 秒
# 注意：请通过环境变量设置 HF_TOKEN，不要在此文件中硬编码
# PowerShell: $env:HF_TOKEN='your_token'
# CMD: set HF_TOKEN=your_token
# 确保缓存目录存在
os.makedirs(LOCAL_DIR, exist_ok=True)
os.makedirs(os.path.join(LOCAL_DIR, "inputs"), exist_ok=True)
os.makedirs(os.path.join(LOCAL_DIR, "outputs"), exist_ok=True)
os.makedirs(os.path.join(LOCAL_DIR, "processing"), exist_ok=True)


def get_api():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("错误: 请设置环境变量 HF_TOKEN")
        print("PowerShell: $env:HF_TOKEN='your_token'")
        sys.exit(1)
    return HfApi(token=token)


def process_task(api, task, locations):
    print(f"[*] 开始处理任务: {task['id']} - {task['photoPath']}")
   
    # 为当前任务创建隔离的工作目录
    task_dir = os.path.join(LOCAL_DIR, "processing", str(task['id']))
    input_dir = os.path.join(task_dir, "input")
    output_dir = os.path.join(task_dir, "output")
   
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)
    os.makedirs(input_dir)
    os.makedirs(output_dir)


    # 1. 下载图片
    try:
        local_image_path = hf_hub_download(
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            filename=task['photoPath'],
            local_dir=LOCAL_DIR
        )
        print(f"    已下载图片: {local_image_path}")
       
        # 将图片复制到隔离的 input 目录，这是 sharp 的输入要求
        # 注意：hf_hub_download 可能会保持原始目录结构，例如 inputs/xxx.jpg
        # 我们将其复制到 input_dir 根目录下
        filename = os.path.basename(local_image_path)
        shutil.copy(local_image_path, os.path.join(input_dir, filename))
       
    except Exception as e:
        print(f"    下载或准备图片失败: {e}")
        return False


    # 2. 调用本地 ml-sharp 进行 3D 重建
    print("    正在调用 ml-sharp 进行 3D 重建...")
   
    # 构建命令: sharp predict -i <input_dir> -o <output_dir>
    # 假设 sharp 已在 PATH 中可用
    cmd = ["sharp", "predict", "-i", input_dir, "-o", output_dir]
   
    try:
        start_time = time.time()
        # capture_output=True 可以捕获输出，但在长时间运行时可能不直观，这里直接让它输出到控制台
        result = subprocess.run(cmd, check=True, text=True)
        elapsed = time.time() - start_time
        print(f"    重建命令执行完毕，耗时: {elapsed:.2f}s")
    except subprocess.CalledProcessError as e:
        print(f"    ml-sharp 执行失败: {e}")
        return False
    except FileNotFoundError:
        print("    错误: 找不到 'sharp' 命令。请确保 ml-sharp 已安装并添加到 PATH。")
        return False


    # 3. 查找生成的 .ply 文件
    # sharp 会在 output_dir 下生成 .ply 文件
    ply_files = glob.glob(os.path.join(output_dir, "*.ply"))
    if not ply_files:
        print("    错误: 输出目录中未找到 .ply 文件")
        return False
   
    # 通常只会生成一个，取第一个
    generated_ply = ply_files[0]
    print(f"    找到模型文件: {generated_ply}")
   
    # 4. 上传结果
    output_filename = f"{task['id']}.ply"
    remote_splat_path = f"outputs/{output_filename}"
   
    try:
        api.upload_file(
            path_or_fileobj=generated_ply,
            path_in_repo=remote_splat_path,
            repo_id=REPO_ID,
            repo_type=REPO_TYPE
        )
        print(f"    结果已上传: {remote_splat_path}")
    except Exception as e:
        print(f"    上传结果失败: {e}")
        return False
       
    # 清理临时文件 (可选)
    # shutil.rmtree(task_dir)


    # 5. 更新本地状态对象
    task['status'] = 'ready'
    task['splatPath'] = remote_splat_path
    return True


def main():
    api = get_api()
    print(f"--- 3DGS 本地计算节点启动 (Powered by ml-sharp) ---")
    print(f"监听仓库: {REPO_ID}")
   
    while True:
        try:
            # 1. 获取任务列表 (locations.json)
            # 为了避免缓存，每次都重新下载或通过API读取
            # 这里简单起见，下载 locations.json
            try:
                local_locations_path = hf_hub_download(
                    repo_id=REPO_ID,
                    repo_type=REPO_TYPE,
                    filename="locations.json",
                    local_dir=LOCAL_DIR,
                    force_download=True # 强制获取最新
                )
                with open(local_locations_path, 'r', encoding='utf-8') as f:
                    locations = json.load(f)
            except Exception as e:
                print(f"无法读取任务列表 (可能尚无文件): {e}")
                locations = []
           
            # 2. 查找待处理任务
            has_updates = False
            for loc in locations:
                if loc.get('status') == 'processing':
                    success = process_task(api, loc, locations)
                    if success:
                        has_updates = True
           
            # 3. 如果有更新，回写 locations.json
            if has_updates:
                print("    正在更新任务状态...")
                # 保存到本地
                updated_json_path = os.path.join(LOCAL_DIR, "locations.json")
                with open(updated_json_path, 'w', encoding='utf-8') as f:
                    json.dump(locations, f, indent=2, ensure_ascii=False)
               
                # 上传
                api.upload_file(
                    path_or_fileobj=updated_json_path,
                    path_in_repo="locations.json",
                    repo_id=REPO_ID,
                    repo_type=REPO_TYPE,
                    commit_message=f"Update job status by GPU Node"
                )
                print("[+] 状态同步完成")
           
        except Exception as e:
            print(f"轮询错误: {e}")
           
        print(f"Waiting {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()