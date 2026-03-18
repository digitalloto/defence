"""
AIMCRS God Mode — Pipeline Task Runner
Manages subprocess execution of pipeline scripts with real-time output capture.
"""

import subprocess
import threading
import uuid
import time
from pathlib import Path
from collections import deque
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Pipeline steps mapped to their script paths
PIPELINE_STEPS = {
    "youtube_download": {
        "script": "scripts/download/youtube_downloader.py",
        "name": "YouTube Downloader",
        "phase": "Download",
        "order": 1,
    },
    "government_download": {
        "script": "scripts/download/government_downloader.py",
        "name": "Government Data",
        "phase": "Download",
        "order": 2,
    },
    "academic_download": {
        "script": "scripts/download/academic_downloader.py",
        "name": "Academic Datasets",
        "phase": "Download",
        "order": 3,
    },
    "kaggle_download": {
        "script": "scripts/download/kaggle_downloader.py",
        "name": "Kaggle Datasets",
        "phase": "Download",
        "order": 4,
    },
    "roboflow_download": {
        "script": "scripts/download/roboflow_downloader.py",
        "name": "Roboflow Datasets",
        "phase": "Download",
        "order": 5,
    },
    "live_feeds": {
        "script": "scripts/download/live_feeds.py",
        "name": "Live Traffic Feeds",
        "phase": "Download",
        "order": 6,
    },
    "process": {
        "script": "scripts/process/process_pipeline.py",
        "name": "Process Pipeline",
        "phase": "Process",
        "order": 7,
    },
    "auto_label": {
        "script": "scripts/label/auto_label.py",
        "name": "Auto Labeller",
        "phase": "Label",
        "order": 8,
    },
    "augment": {
        "script": "scripts/process/augment.py",
        "name": "Data Augmentation",
        "phase": "Augment",
        "order": 9,
    },
    "train_ambulance": {
        "script": "scripts/train/train_ambulance.py",
        "name": "Train Ambulance Model",
        "phase": "Train",
        "order": 10,
    },
    "train_flow": {
        "script": "scripts/train/train_flow.py",
        "name": "Train Flow Model",
        "phase": "Train",
        "order": 11,
    },
    "viltics_comparison": {
        "script": "scripts/train/viltics_comparison.py",
        "name": "VILTICS Comparison",
        "phase": "Evaluate",
        "order": 12,
    },
}


class TaskRunner:
    """Manages pipeline task execution with output capture."""

    def __init__(self):
        self.tasks = {}  # task_id -> task info
        self.lock = threading.Lock()

    def run_step(self, step_name):
        """Start a pipeline step in a subprocess. Returns task_id."""
        if step_name not in PIPELINE_STEPS:
            return None, f"Unknown step: {step_name}"

        # Check if already running
        with self.lock:
            for tid, task in self.tasks.items():
                if task["step"] == step_name and task["status"] == "running":
                    return None, f"Step '{step_name}' is already running (task {tid})"

        step = PIPELINE_STEPS[step_name]
        script_path = PROJECT_ROOT / step["script"]

        if not script_path.exists():
            return None, f"Script not found: {step['script']}"

        task_id = str(uuid.uuid4())[:8]
        task_info = {
            "id": task_id,
            "step": step_name,
            "name": step["name"],
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "exit_code": None,
            "output": deque(maxlen=500),
            "error": "",
        }

        with self.lock:
            self.tasks[task_id] = task_info

        thread = threading.Thread(
            target=self._execute, args=(task_id, script_path), daemon=True
        )
        thread.start()

        return task_id, None

    def _execute(self, task_id, script_path):
        """Execute a script and capture output."""
        try:
            proc = subprocess.Popen(
                ["python3", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
                text=True,
                bufsize=1,
            )

            with self.lock:
                self.tasks[task_id]["pid"] = proc.pid

            for line in proc.stdout:
                with self.lock:
                    self.tasks[task_id]["output"].append(line.rstrip())

            proc.wait()

            with self.lock:
                self.tasks[task_id]["status"] = (
                    "complete" if proc.returncode == 0 else "error"
                )
                self.tasks[task_id]["exit_code"] = proc.returncode
                self.tasks[task_id]["finished_at"] = datetime.now().isoformat()

        except Exception as e:
            with self.lock:
                self.tasks[task_id]["status"] = "error"
                self.tasks[task_id]["error"] = str(e)
                self.tasks[task_id]["finished_at"] = datetime.now().isoformat()

    def get_task(self, task_id):
        """Get task status and output."""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            return {
                "id": task["id"],
                "step": task["step"],
                "name": task["name"],
                "status": task["status"],
                "started_at": task["started_at"],
                "finished_at": task["finished_at"],
                "exit_code": task["exit_code"],
                "output": list(task["output"]),
                "error": task["error"],
            }

    def get_all_tasks(self):
        """Get summary of all tasks."""
        with self.lock:
            return [
                {
                    "id": t["id"],
                    "step": t["step"],
                    "name": t["name"],
                    "status": t["status"],
                    "started_at": t["started_at"],
                    "finished_at": t["finished_at"],
                }
                for t in self.tasks.values()
            ]


# Singleton instance
runner = TaskRunner()
