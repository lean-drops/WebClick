import os
import logging
import hashlib
import asyncio
import shutil
import threading
import time
import uuid
from typing import List

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json

from app.processing.website_downloader import (
    PDFConverter,
    merge_pdfs_with_bookmarks,
    apply_ocr_to_all_pdfs,
    create_zip_archive
)
from app.scrapers.scraping_helpers import (
    scrape_lock,
    scrape_tasks,
    run_scrape_task,
    render_links_recursive
)
from config import MAPPING_CACHE_DIR, logger, OUTPUT_PDFS_DIR, BASE_DIR, TEMPLATES_DIR, STATIC_DIR

main_router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))

pdf_tasks = {}
pdf_lock = threading.Lock()

@main_router.get("/")
async def index(request: Request):
    version = str(int(time.time()))
    return templates.TemplateResponse("index.html", {"request": request, "version": version})

@main_router.post("/scrape_links")
async def scrape(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    url = form_data.get("url")
    logger.info(f"Scrape request received for URL: {url}")

    if not url:
        raise HTTPException(status_code=400, detail="No URL provided.")

    try:
        task_id = hashlib.md5(url.encode()).hexdigest()
        cache_filename = f"{task_id}.json"
        cache_filepath = os.path.join(MAPPING_CACHE_DIR, cache_filename)

        if os.path.exists(cache_filepath):
            with scrape_lock:
                with open(cache_filepath, "r", encoding="utf-8") as f:
                    cached_url_mapping = json.load(f)
                scrape_tasks[task_id] = {
                    "status": "completed",
                    "result": {"url_mapping": cached_url_mapping}
                }
            return RedirectResponse(url=f"/scrape_result/{task_id}", status_code=303)

        background_tasks.add_task(start_scrape_task, task_id, url)
        logger.info(f"No cached data found. Scraping started for URL: {url}")
        return RedirectResponse(url=f"/scrape_status/{task_id}")

    except Exception as e:
        logger.error(f"Error starting scraping: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def start_scrape_task(task_id, url):
    asyncio.run(run_scrape_task(task_id, url))

@main_router.get("/scrape_status/{task_id}")
async def scrape_status(request: Request, task_id: str):
    logger.debug(f"Accessed scrape_status for task_id: {task_id}")
    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task_info["status"] == "completed":
        return RedirectResponse(url=f"/scrape_result/{task_id}")
    elif task_info["status"] == "failed":
        error_message = task_info.get("error", "Unknown error.")
        raise HTTPException(status_code=500, detail=error_message)
    else:
        return templates.TemplateResponse("scrape_status.html", {"request": request, "task_id": task_id})

@main_router.get("/get_status/{task_id}")
async def get_status(task_id: str):
    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        return JSONResponse({"status": "not_found"})

    response_data = {
        "status": task_info["status"],
        "error": task_info.get("error", None),
        "url_mapping": task_info["result"].get("url_mapping", None) if task_info["status"] == "completed" else None
    }
    return JSONResponse(response_data)

@main_router.get("/scrape_result/{task_id}")
async def scrape_result(request: Request, task_id: str):
    cache_filename = f"{task_id}.json"
    cache_filepath = os.path.join(MAPPING_CACHE_DIR, cache_filename)
    if not os.path.exists(cache_filepath):
        raise HTTPException(status_code=404, detail="Result not found.")

    with open(cache_filepath, "r", encoding="utf-8") as f:
        result = json.load(f)
        url_mapping = result.get("url_mapping")
        base_page_id = result.get("base_page_id")

    links_html = render_links_recursive(url_mapping, base_page_id)
    main_link_url = url_mapping.get(base_page_id, {}).get("url", "#")
    main_link_title = url_mapping.get(base_page_id, {}).get("title", "No Title")

    return templates.TemplateResponse(
        "scrape_result.html",
        {
            "request": request,
            "links_html": links_html,
            "url_mapping": url_mapping,
            "base_page_id": base_page_id,
            "main_link_url": main_link_url,
            "main_link_title": main_link_title,
        },
    )

@main_router.post("/start_pdf_task")
async def start_pdf_task(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    selected_links = data.get("selected_links", [])
    conversion_mode = data.get("conversion_mode", "collapsed")

    if not selected_links:
        return JSONResponse({"status": "error", "message": "Keine Links ausgewählt."}, status_code=400)
    if conversion_mode not in ["collapsed", "expanded"]:
        return JSONResponse({"status": "error", "message": "Ungültiger Konvertierungsmodus."}, status_code=400)

    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_pdf_task, task_id, selected_links, conversion_mode)
    logger.info(f"PDF task started with Task-ID: {task_id} and mode: {conversion_mode}")

    return JSONResponse({"status": "success", "task_id": task_id})

async def run_pdf_task(task_id: str, urls: List[str], conversion_mode: str):
    with pdf_lock:
        pdf_tasks[task_id] = {"status": "running", "result": {}, "error": None}

    try:
        await _run_pdf_task(task_id, urls, conversion_mode)
    except Exception as e:
        logger.error(f"Error in PDF task {task_id}: {e}")
        with pdf_lock:
            pdf_tasks[task_id]["status"] = "failed"
            pdf_tasks[task_id]["error"] = str(e)

async def _run_pdf_task(task_id: str, urls: List[str], conversion_mode: str):
    pdf_converter = PDFConverter(max_concurrent_tasks=20)
    await pdf_converter.initialize()

    pdf_entries = []
    if conversion_mode == "collapsed":
        logger.info(f"Converting URLs to PDFs (collapsed) for Task-ID: {task_id}.")
        collapsed_results = await pdf_converter.convert_urls_to_pdfs(urls, expanded=False)
        pdf_entries.extend(collapsed_results)
        merged_collapsed_pdf = os.path.join(OUTPUT_PDFS_DIR, f"combined_pdfs_collapsed_{task_id}.pdf")
        merge_pdfs_with_bookmarks(collapsed_results, merged_collapsed_pdf)
    elif conversion_mode == "expanded":
        logger.info(f"Converting URLs to PDFs (expanded) for Task-ID: {task_id}.")
        expanded_results = await pdf_converter.convert_urls_to_pdfs(urls, expanded=True)
        pdf_entries.extend(expanded_results)
        merged_expanded_pdf = os.path.join(OUTPUT_PDFS_DIR, f"combined_pdfs_expanded_{task_id}.pdf")
        merge_pdfs_with_bookmarks(expanded_results, merged_expanded_pdf)

    await pdf_converter.close()

    apply_ocr_to_all_pdfs(
        individual_collapsed_dir=pdf_converter.output_dir_collapsed,
        individual_expanded_dir=pdf_converter.output_dir_expanded,
        merged_collapsed_pdf=merged_collapsed_pdf if conversion_mode == "collapsed" else None,
        merged_expanded_pdf=merged_expanded_pdf if conversion_mode == "expanded" else None
    )

    zip_filename = os.path.join(OUTPUT_PDFS_DIR, f"output_pdfs_{task_id}.zip")
    create_zip_archive(OUTPUT_PDFS_DIR, zip_filename)

    for item in os.listdir(OUTPUT_PDFS_DIR):
        item_path = os.path.join(OUTPUT_PDFS_DIR, item)
        if item_path != zip_filename:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

    with pdf_lock:
        pdf_tasks[task_id]["status"] = "completed"
        pdf_tasks[task_id]["result"] = {"zip_file": zip_filename}

    logger.info(f"PDF task completed: {task_id}")

@main_router.get("/pdf_status/{task_id}")
async def pdf_status(request: Request, task_id: str):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail="PDF Task not found.")
    if task_info["status"] == "completed":
        return RedirectResponse(url=f"/pdf_result/{task_id}")
    elif task_info["status"] == "failed":
        error_message = task_info.get("error", "Unknown error.")
        raise HTTPException(status_code=500, detail=error_message)
    else:
        return templates.TemplateResponse("pdf_status.html", {"request": request, "task_id": task_id})

@main_router.get("/get_pdf_status/{task_id}")
async def get_pdf_status(task_id: str):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        return JSONResponse({"status": "not_found"})

    response_data = {
        "status": task_info["status"],
        "error": task_info.get("error", None),
    }
    return JSONResponse(response_data)

@main_router.get("/pdf_result/{task_id}")
async def pdf_result(request: Request, task_id: str):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task_info["status"] == "failed":
        error_message = task_info.get("error", "Unknown error.")
        raise HTTPException(status_code=500, detail=error_message)
    if task_info["status"] != "completed":
        return RedirectResponse(url=f"/pdf_status/{task_id}")

    zip_file_path = task_info["result"].get("zip_file")
    if not zip_file_path or not os.path.exists(zip_file_path):
        raise HTTPException(status_code=404, detail="ZIP file not found.")

    return templates.TemplateResponse(
        "convert_result.html",
        {"request": request, "zip_filename": os.path.basename(zip_file_path), "task_id": task_id},
    )

@main_router.get("/download_pdfs/{task_id}")
async def download_pdfs(task_id: str):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail="PDF Task not found.")
    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="PDF Task is not yet completed.")

    zip_file_path = task_info["result"].get("zip_file")
    if not zip_file_path or not os.path.exists(zip_file_path):
        raise HTTPException(status_code=404, detail="ZIP file not found.")

    return FileResponse(path=zip_file_path, filename=os.path.basename(zip_file_path), media_type="application/zip")
