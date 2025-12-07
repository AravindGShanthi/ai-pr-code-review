import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_ruff_on_code(files: list):
    results = []
    ruff_path = shutil.which("ruff")
    if not ruff_path:
        return [{"error": "ruff command not found in PATH"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for f in files:
            safe_name = f["filename"].replace("/", "_")
            file_path = tmp_path / safe_name

            file_path.write_text(f["content"], encoding="utf-8")
            print(file_path.read_text())
            try:
                proc = subprocess.run(  # noqa: S603
                    [ruff_path, "check", "--output-format", "json", str(file_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if proc.stdout.strip():
                    results.extend(json.loads(proc.stdout))
            except (OSError, json.JSONDecodeError) as e:
                results.append({"file": f["filename"], "error": str(e)})

    return results
