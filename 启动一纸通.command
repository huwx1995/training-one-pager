#!/bin/zsh

SCRIPT_DIR="${0:A:h}"
APP_PORT="${PORT:-8011}"
RUNTIME_DIR="$SCRIPT_DIR/uploads"
OPEN_BROWSER="${OPEN_BROWSER:-1}"

cd "$SCRIPT_DIR" || exit 1

if [[ -z "${PORT:-}" ]]; then
  while nc -z 127.0.0.1 "$APP_PORT" >/dev/null 2>&1; do
    (( APP_PORT++ ))
    if (( APP_PORT > 8020 )); then
      echo "8011—8020 端口均被占用，请关闭旧服务后重试。"
      read -k 1 "?按任意键关闭窗口……"
      exit 1
    fi
  done
elif nc -z 127.0.0.1 "$APP_PORT" >/dev/null 2>&1; then
  echo "指定端口 $APP_PORT 已被占用，请关闭旧服务或更换 PORT。"
  read -k 1 "?按任意键关闭窗口……"
  exit 1
fi

APP_URL="http://127.0.0.1:$APP_PORT"
LOG_FILE="$RUNTIME_DIR/server-$APP_PORT.log"
PID_FILE="$RUNTIME_DIR/server-$APP_PORT.pid"

open_page() {
  if [[ "$OPEN_BROWSER" != "0" ]]; then
    open "$APP_URL"
  fi
}

python_has_dependencies() {
  "$1" -c 'import PIL, docx, pptx, pypdf' >/dev/null 2>&1
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -n "$PYTHON_BIN" ]] && ! python_has_dependencies "$PYTHON_BIN"; then
  PYTHON_BIN=""
fi
if [[ -z "$PYTHON_BIN" && -x "$SCRIPT_DIR/.venv/bin/python3" ]] && python_has_dependencies "$SCRIPT_DIR/.venv/bin/python3"; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"
fi
if [[ -z "$PYTHON_BIN" ]] && command -v python3 >/dev/null 2>&1; then
  SYSTEM_PYTHON="$(command -v python3)"
  if python_has_dependencies "$SYSTEM_PYTHON"; then
    PYTHON_BIN="$SYSTEM_PYTHON"
  fi
fi
if [[ -z "$PYTHON_BIN" ]]; then
  echo "没有找到已安装项目依赖的 Python 3 环境。"
  echo "请在项目目录中执行："
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/python3 -m pip install -r requirements.txt"
  echo "PDF 定位与图片粗筛建议安装 PyMuPDF；不会下载模型权重。"
  read -k 1 "?按任意键关闭窗口……"
  exit 1
fi

mkdir -p "$RUNTIME_DIR"

if ! "$PYTHON_BIN" -c 'import pymupdf' >/dev/null 2>&1; then
  echo "提示：当前 Python 缺少 PyMuPDF。TXT、Word、PPT 与一纸通功能可用；PDF 将使用兼容解析，图片定位能力受限。"
fi

echo "正在启动一纸通（端口 $APP_PORT）……"
echo "浏览器会自动打开。使用期间请保留这个终端窗口；结束使用后可以关闭。"
(
  for attempt in {1..40}; do
    if curl -fsS "$APP_URL" >/dev/null 2>&1; then
      open_page
      exit 0
    fi
    sleep 0.25
  done
  echo "服务启动后未能自动打开页面，请查看：$LOG_FILE"
) &

print -r -- "$$" > "$PID_FILE"
exec env PORT="$APP_PORT" MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-1024}" PYTHONUNBUFFERED=1 "$PYTHON_BIN" "$SCRIPT_DIR/server.py" 2>&1 | tee -a "$LOG_FILE"
