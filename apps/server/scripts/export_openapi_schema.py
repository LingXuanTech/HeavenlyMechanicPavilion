"""
导出 FastAPI OpenAPI schema 为 JSON 文件

用于 CI 流水线中前后端类型一致性校验：
  python scripts/export_openapi_schema.py          # 输出到 openapi.json
  python scripts/export_openapi_schema.py -o /tmp  # 指定输出目录
"""
import json
import os
import sys
from pathlib import Path

# 确保 apps/server 在 sys.path 中
SERVER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_DIR))

# 设置 mock 环境变量，避免 settings 启动校验报错
os.environ.setdefault("ENV", "development")
os.environ.setdefault("DATABASE_MODE", "sqlite")
os.environ.setdefault("DATABASE_URL", "sqlite:///./db/trading.db")

from main import app  # noqa: E402


def main() -> None:
    output_dir = SERVER_DIR
    if len(sys.argv) > 2 and sys.argv[1] == "-o":
        output_dir = Path(sys.argv[2])

    schema = app.openapi()
    output_path = output_dir / "openapi.json"
    output_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OpenAPI schema exported to {output_path}")


if __name__ == "__main__":
    main()
