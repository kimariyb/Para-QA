# Copyright (c) Opendatalab. All rights reserved.
"""
MinerU 3.2.0 串行批处理脚本（基于官方 demo.py 改写）

- 逐文件处理，一个出错不影响后续
- 失败文件记录到 failed_files.log
- 完成后打印汇总

用法：
  python mineru_batch.py                        # 使用脚本内默认参数
  python mineru_batch.py --input ./pdfs --output ./out
  python mineru_batch.py --input ./pdfs --output ./out --backend pipeline --lang en
  python mineru_batch.py --input ./pdfs --output ./out --api-url http://127.0.0.1:8000
"""

import argparse
import asyncio
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

import httpx

from mineru.cli import api_client as _api_client
from mineru.cli.common import image_suffixes, office_suffixes, pdf_suffixes
from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path

SUPPORTED_INPUT_SUFFIXES = set(pdf_suffixes + image_suffixes + office_suffixes)


# ─────────────────────────── 日志 ────────────────────────────────

def setup_logging(output_dir: Path) -> logging.Logger:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "batch.log"

    logger = logging.getLogger("mineru_batch")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # 控制台
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    # 文件（记录 DEBUG 以上全部）
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


# ─────────────────────────── 工具函数 ────────────────────────────

def collect_input_files(input_path: str | Path) -> list[Path]:
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"输入路径不存在：{path}")

    if path.is_file():
        suffix = guess_suffix_by_path(path)
        if suffix not in SUPPORTED_INPUT_SUFFIXES:
            raise ValueError(f"不支持的文件类型：{path.name}")
        return [path]

    if not path.is_dir():
        raise ValueError(f"输入路径必须是文件或目录：{path}")

    files = sorted(
        c.resolve()
        for c in path.iterdir()
        if c.is_file() and guess_suffix_by_path(c) in SUPPORTED_INPUT_SUFFIXES
    )
    if not files:
        raise ValueError(f"目录中没有受支持的文件：{path}")
    return files


def prepare_local_api_temp_dir() -> None:
    """WSL 环境下修正 TMPDIR，避免 vLLM/ZeroMQ IPC socket 报错（来自官方 demo）"""
    current_temp_dir = Path(tempfile.gettempdir())
    if os.name == "nt" or not Path("/tmp").exists():
        return
    if not str(current_temp_dir).startswith("/mnt/"):
        return
    os.environ["TMPDIR"] = "/tmp"
    tempfile.tempdir = None


def build_form_data(args: argparse.Namespace) -> dict:
    return _api_client.build_parse_request_form_data(
        lang_list=[args.lang],
        backend=args.backend,
        parse_method=args.method,
        formula_enable=args.formula,
        table_enable=args.table,
        image_analysis=args.image_analysis,
        server_url=args.url or None,
        start_page_id=args.start,
        end_page_id=args.end,
        return_md=True,
        return_middle_json=True,
        return_model_output=False,
        return_content_list=True,
        return_images=True,
        response_format_zip=True,
        return_original_file=False,
    )


# ─────────────────────────── 单文件处理 ──────────────────────────

async def process_one(
    file_path: Path,
    output_dir: Path,
    form_data: dict,
    http_client: httpx.AsyncClient,
    server_health: _api_client.ServerHealth,
    logger: logging.Logger,
) -> None:
    """处理单个文件，出错时直接抛出异常（由调用方捕获）"""
    upload_asset = _api_client.UploadAsset(
        path=file_path,
        upload_name=file_path.name,
    )

    logger.info(f"[{file_path.name}] 提交任务...")
    submit_response = await _api_client.submit_parse_task(
        base_url=server_health.base_url,
        upload_assets=[upload_asset],
        form_data=form_data,
    )
    logger.debug(f"[{file_path.name}] task_id={submit_response.task_id}")

    last_status = None

    def on_status_update(snapshot: _api_client.TaskStatusSnapshot) -> None:
        nonlocal last_status
        msg = (
            snapshot.status
            if snapshot.queued_ahead is None
            else f"{snapshot.status} (queued_ahead={snapshot.queued_ahead})"
        )
        if msg != last_status:
            last_status = msg
            logger.debug(f"[{file_path.name}] status={msg}")

    await _api_client.wait_for_task_result(
        client=http_client,
        submit_response=submit_response,
        task_label=file_path.name,
        status_snapshot_callback=on_status_update,
    )

    result_zip_path = await _api_client.download_result_zip(
        client=http_client,
        submit_response=submit_response,
        task_label=file_path.name,
    )

    file_output_dir = output_dir / file_path.stem
    file_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        _api_client.safe_extract_zip(result_zip_path, file_output_dir)
    finally:
        result_zip_path.unlink(missing_ok=True)

    logger.info(f"[{file_path.name}] ✓ 完成，结果保存至 {file_output_dir}")


# ─────────────────────────── 批处理主流程 ────────────────────────

async def run_batch(
    input_files: list[Path],
    output_dir: Path,
    args: argparse.Namespace,
    logger: logging.Logger,
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """
    串行处理所有文件。
    返回 (成功列表, 失败列表)，失败列表元素为 (文件路径, 错误信息)。
    """
    form_data = build_form_data(args)
    succeeded: list[Path] = []
    failed: list[tuple[Path, str]] = []

    local_server: _api_client.LocalAPIServer | None = None

    async with httpx.AsyncClient(
        timeout=_api_client.build_http_timeout(),
        follow_redirects=True,
    ) as http_client:
        # ── 启动/连接 API 服务（只做一次）──
        try:
            if args.api_url is None:
                prepare_local_api_temp_dir()
                local_server = _api_client.LocalAPIServer()
                base_url = local_server.start()
                logger.info(f"已启动本地 mineru-api：{base_url}")
                server_health = await _api_client.wait_for_local_api_ready(
                    http_client, local_server
                )
            else:
                server_health = await _api_client.fetch_server_health(
                    http_client,
                    _api_client.normalize_base_url(args.api_url),
                )
            logger.info(f"使用 API：{server_health.base_url}")
        except Exception as e:
            logger.error(f"无法连接 mineru-api：{e}")
            raise

        # ── 逐文件串行处理 ──
        try:
            for idx, fp in enumerate(input_files, 1):
                logger.info(f"─── [{idx}/{len(input_files)}] {fp.name} ───")
                try:
                    await process_one(
                        file_path=fp,
                        output_dir=output_dir,
                        form_data=form_data,
                        http_client=http_client,
                        server_health=server_health,
                        logger=logger,
                    )
                    succeeded.append(fp)
                except Exception as e:
                    err_msg = f"{type(e).__name__}: {e}"
                    logger.error(f"[{fp.name}] ✗ 失败：{err_msg}")
                    failed.append((fp, err_msg))
                    # 继续处理下一个文件
                    continue
        finally:
            if local_server is not None:
                local_server.stop()
                logger.debug("本地 mineru-api 已停止")

    return succeeded, failed


# ─────────────────────────── 写入失败日志 ────────────────────────

def write_failed_log(
    failed: list[tuple[Path, str]],
    output_dir: Path,
    logger: logging.Logger,
) -> None:
    if not failed:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_dir / f"failed_files_{ts}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# MinerU 批处理失败记录  {datetime.now().isoformat()}\n")
        f.write(f"# 共 {len(failed)} 个文件失败\n\n")
        for fp, reason in failed:
            f.write(f"{fp}\n    原因：{reason}\n\n")
    logger.warning(f"失败文件已记录至：{log_path}")


# ─────────────────────────── 参数解析 ────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MinerU 3.2.0 串行批处理",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input",  "-i", default="./pdfs",   help="输入文件或目录")
    p.add_argument("--output", "-o", default="./output", help="输出根目录")
    p.add_argument("--api-url",      default=None,
                   help="mineru-api 地址，如 http://127.0.0.1:8000；留空则自动启动本地服务")

    p.add_argument("-b", "--backend", default="hybrid-auto-engine",
                   choices=["pipeline","vlm-http-client","hybrid-http-client",
                             "vlm-auto-engine","hybrid-auto-engine"],
                   help="解析后端")
    p.add_argument("-m", "--method",  default="auto",
                   choices=["auto","txt","ocr"],
                   help="PDF 解析方式（pipeline / hybrid-* 有效）")
    p.add_argument("-l", "--lang",    default="ch",
                   choices=["ch","ch_server","ch_lite","en","korean","japan",
                             "chinese_cht","ta","te","ka","th","el",
                             "latin","arabic","east_slavic","cyrillic","devanagari"],
                   help="文档语言")
    p.add_argument("-u", "--url",     default=None,
                   help="VLM/Hybrid HTTP 服务地址（*-http-client 必填）")
    p.add_argument("-s", "--start",   type=int, default=0,    help="起始页（从 0 开始）")
    p.add_argument("-e", "--end",     type=int, default=None, help="结束页（从 0 开始）")
    p.add_argument("-f", "--formula", type=lambda x: x.lower() != "false",
                   default=True, metavar="BOOL", help="启用公式解析")
    p.add_argument("-t", "--table",   type=lambda x: x.lower() != "false",
                   default=True, metavar="BOOL", help="启用表格解析")
    p.add_argument("--image-analysis", dest="image_analysis",
                   type=lambda x: x.lower() != "false",
                   default=True, metavar="BOOL",
                   help="启用图像/图表分析（VLM / hybrid 有效）")
    return p.parse_args()


# ─────────────────────────── 入口 ────────────────────────────────

def main() -> None:
    args = parse_args()
    output_dir = Path(args.output).resolve()

    logger = setup_logging(output_dir)
    logger.info("=" * 55)
    logger.info("MinerU 3.2.0 批处理启动")
    logger.info(f"  输入：{args.input}")
    logger.info(f"  输出：{args.output}")
    logger.info(f"  backend={args.backend}  method={args.method}  lang={args.lang}")
    logger.info("=" * 55)

    # 可选：设置模型下载源
    os.environ["MINERU_MODEL_SOURCE"] = "modelscope"

    try:
        input_files = collect_input_files(args.input)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        raise SystemExit(1)

    logger.info(f"共 {len(input_files)} 个文件待处理")

    succeeded, failed = asyncio.run(
        run_batch(input_files, output_dir, args, logger)
    )

    # 写入失败日志
    write_failed_log(failed, output_dir, logger)

    # 汇总
    logger.info("=" * 55)
    logger.info(f"批处理完成  共 {len(input_files)} 个文件")
    logger.info(f"  ✓ 成功：{len(succeeded)}  ✗ 失败：{len(failed)}")
    if failed:
        logger.warning("失败文件列表：")
        for fp, reason in failed:
            logger.warning(f"  - {fp.name}  ({reason})")
    logger.info("=" * 55)

    raise SystemExit(0 if not failed else 1)


if __name__ == "__main__":
    main()