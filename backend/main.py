import os
import signal
import subprocess
import asyncio
import logging
import yaml
import psutil
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# 配置日志：同时输出到文件和控制台，确保中文编码正确
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_layer")

app = FastAPI(title="Papermill API")

# 全局变量，用于存储 orchestrator 进程对象
ORCHESTRATOR_PROCESS = None
WORKSPACE_DIR = "src/workspace"
CONFIG_PATH = "config.yaml"
LOG_PATH = "system.log"

# 数据模型：配置更新请求
class ConfigUpdate(BaseModel):
    research_directions: Optional[List[str]] = None
    max_concurrent_pipelines: Optional[int] = None
    llm_model: Optional[str] = None
    max_ideas_per_cycle: Optional[int] = None
    hypothesis_review_threshold: Optional[int] = None
    experiment_timeout_minutes: Optional[int] = None
    auto_commit: Optional[bool] = None

# 辅助函数：获取 orchestrator 进程状态
def get_orchestrator_status():
    global ORCHESTRATOR_PROCESS
    if ORCHESTRATOR_PROCESS and ORCHESTRATOR_PROCESS.poll() is None:
        return "running"
    return "stopped"

# 辅助函数：获取单条流水线的详细信息
def get_pipeline_details(idea_id: str):
    idea_path = os.path.join(WORKSPACE_DIR, "ideas", f"{idea_id}.md")
    if not os.path.exists(idea_path):
        return None

    status = "pending"
    stage = "ideation"

    # 检查各阶段产物以推断进度
    if os.path.exists(os.path.join(WORKSPACE_DIR, "experiments", idea_id)):
        status = "running"
        stage = "planning"

    if os.path.exists(os.path.join(WORKSPACE_DIR, "results", f"{idea_id}.json")):
        status = "running"
        stage = "experiment"

    if os.path.exists(os.path.join(WORKSPACE_DIR, "latex", idea_id)):
        status = "running"
        stage = "writing"

    pdf_path = os.path.join(WORKSPACE_DIR, "results", f"{idea_id}.pdf")
    if os.path.exists(pdf_path):
        status = "completed"
        stage = "writing"

    return {
        "id": idea_id,
        "status": status,
        "stage": stage,
        "title": idea_id, # 简化处理，实际应解析 markdown
        "updated_at": os.path.getmtime(idea_path)
    }

# --- API 路由 ---

# 系统控制：启动 orchestrator 后台进程
@app.post("/api/v1/system/start")
async def start_system():
    global ORCHESTRATOR_PROCESS
    if get_orchestrator_status() == "running":
        return {"message": "系统已在运行中"}

    try:
        # 启动 orchestrator.py，使用 -u 参数保证 stdout 无缓冲，方便日志实时捕获
        ORCHESTRATOR_PROCESS = subprocess.Popen(
            ["python3", "-u", "src/orchestrator.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        logger.info(f"Orchestrator 已启动，PID: {ORCHESTRATOR_PROCESS.pid}")
        return {"message": "系统启动成功", "pid": ORCHESTRATOR_PROCESS.pid}
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 系统控制：停止 orchestrator 及其所有子进程
@app.post("/api/v1/system/stop")
async def stop_system():
    global ORCHESTRATOR_PROCESS
    if not ORCHESTRATOR_PROCESS or ORCHESTRATOR_PROCESS.poll() is not None:
        return {"message": "系统未运行"}

    try:
        # 使用 psutil 递归终止所有子进程
        parent = psutil.Process(ORCHESTRATOR_PROCESS.pid)
        for child in parent.children(recursive=True):
            child.terminate()
        parent.terminate()

        # 等待进程退出，若超时则强制杀死
        gone, alive = psutil.wait_procs([parent], timeout=3)
        for p in alive:
            p.kill()

        ORCHESTRATOR_PROCESS = None
        logger.info("Orchestrator 已停止")
        return {"message": "系统已停止"}
    except Exception as e:
        logger.error(f"系统停止失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 系统控制：获取运行状态
@app.get("/api/v1/system/status")
async def get_status():
    return {"status": get_orchestrator_status()}

# 配置管理：读取 config.yaml
@app.get("/api/v1/config")
async def get_config():
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="配置文件不存在")
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

# 配置管理：更新 config.yaml
@app.put("/api/v1/config")
async def update_config(update: ConfigUpdate):
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="配置文件不存在")

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 仅更新请求中提供的字段
    update_data = update.dict(exclude_unset=True)
    config.update(update_data)

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    return {"message": "配置已更新", "config": config}

# 研究任务：获取所有已生成的假设列表
@app.get("/api/v1/ideas")
async def get_ideas():
    ideas_dir = os.path.join(WORKSPACE_DIR, "ideas")
    if not os.path.exists(ideas_dir):
        return []

    ideas = []
    for f in os.listdir(ideas_dir):
        if f.endswith(".md"):
            idea_path = os.path.join(ideas_dir, f)
            with open(idea_path, 'r', encoding='utf-8') as file:
                content = file.read()
            ideas.append({
                "id": f.replace(".md", ""),
                "filename": f,
                "content": content,
                "mtime": os.path.getmtime(idea_path)
            })
    # 按修改时间降序排列
    return sorted(ideas, key=lambda x: x["mtime"], reverse=True)

# 研究任务：获取特定假设详情
@app.get("/api/v1/ideas/{idea_id}")
async def get_idea(idea_id: str):
    idea_path = os.path.join(WORKSPACE_DIR, "ideas", f"{idea_id}.md")
    if not os.path.exists(idea_path):
        raise HTTPException(status_code=404, detail="想法不存在")
    with open(idea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return {"id": idea_id, "content": content}

# 研究任务：获取所有流水线状态
@app.get("/api/v1/pipelines")
async def get_pipelines():
    pipelines = []
    ideas_dir = os.path.join(WORKSPACE_DIR, "ideas")
    if not os.path.exists(ideas_dir):
        return []

    for f in os.listdir(ideas_dir):
        if f.endswith(".md"):
            idea_id = f.replace(".md", "")
            details = get_pipeline_details(idea_id)
            if details:
                pipelines.append(details)
    return pipelines

# 研究任务：获取单条流水线详细进度
@app.get("/api/v1/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    details = get_pipeline_details(pipeline_id)
    if not details:
        raise HTTPException(status_code=404, detail="流水线不存在")
    return details

# 论文结果：获取所有论文列表
@app.get("/api/v1/papers")
async def get_papers():
    results_dir = os.path.join(WORKSPACE_DIR, "results")
    if not os.path.exists(results_dir):
        return []

    papers = []
    for f in os.listdir(results_dir):
        if f.endswith(".pdf"):
            paper_id = f.replace(".pdf", "")
            metadata = {}
            json_path = os.path.join(results_dir, f"{paper_id}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as jf:
                        metadata = json.load(jf)
                except:
                    pass

            papers.append({
                "id": paper_id,
                "title": metadata.get("title", paper_id),
                "abstract": metadata.get("abstract", ""),
                "created_at": os.path.getmtime(os.path.join(results_dir, f))
            })
    return sorted(papers, key=lambda x: x["created_at"], reverse=True)

# 论文结果：获取某篇论文的元数据
@app.get("/api/v1/papers/{paper_id}")
async def get_paper(paper_id: str):
    results_dir = os.path.join(WORKSPACE_DIR, "results")
    pdf_path = os.path.join(results_dir, f"{paper_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="论文不存在")

    metadata = {}
    json_path = os.path.join(results_dir, f"{paper_id}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as jf:
                metadata = json.load(jf)
        except:
            pass

    return {
        "id": paper_id,
        "title": metadata.get("title", paper_id),
        "abstract": metadata.get("abstract", ""),
        "created_at": os.path.getmtime(pdf_path)
    }

# 论文结果：下载 PDF
@app.get("/api/v1/papers/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str):
    pdf_path = os.path.join(WORKSPACE_DIR, "results", f"{paper_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF 不存在")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{paper_id}.pdf")

# 论文结果：查看 LaTeX 源码
@app.get("/api/v1/papers/{paper_id}/tex")
async def get_paper_tex(paper_id: str):
    tex_dir = os.path.join(WORKSPACE_DIR, "latex", paper_id)
    if not os.path.exists(tex_dir):
        raise HTTPException(status_code=404, detail="LaTeX 源码不存在")

    for f in os.listdir(tex_dir):
        if f.endswith(".tex"):
            with open(os.path.join(tex_dir, f), 'r', encoding='utf-8') as file:
                return {"content": file.read()}

    raise HTTPException(status_code=404, detail="未找到 .tex 文件")

# 日志：获取最新系统日志
@app.get("/api/v1/logs")
async def get_logs(lines: int = 100):
    if not os.path.exists(LOG_PATH):
        return {"logs": ""}

    try:
        # 修正：将 -n 和 行数 分开传递，避免 tail 命令执行失败
        result = subprocess.run(["tail", "-n", str(lines), LOG_PATH], capture_output=True, text=True)
        return {"logs": result.stdout}
    except Exception as e:
        return {"error": str(e)}

# SSE：实时推送日志流
@app.get("/api/v1/logs/stream")
async def stream_logs():
    async def log_generator():
        if not os.path.exists(LOG_PATH):
            yield "data: [系统日志尚未生成]\n\n"
            return

        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                yield f"data: {line}\n\n"

    return EventSourceResponse(log_generator())

# SSE：实时推送流水线状态变更
@app.get("/api/v1/pipelines/stream")
async def stream_pipelines():
    async def pipeline_generator():
        last_state = None
        while True:
            pipelines = await get_pipelines()
            current_state = json.dumps(pipelines)
            if current_state != last_state:
                yield f"data: {current_state}\n\n"
                last_state = current_state
            await asyncio.sleep(2)

    return EventSourceResponse(pipeline_generator())

# 托管前端静态文件
if os.path.exists("backend/static"):
    app.mount("/", StaticFiles(directory="backend/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)
