from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import FileResponse
import io
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import logging
from typing import List
from file_processor import process_reimbursement_form

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.post("/upload")
async def upload_files(
    request: Request,
    form_file: UploadFile = File(...),
    receipt_files: List[UploadFile] = File(...),
    model_name: str = Form("llama3.2:latest")
):
    """Receives form + receipts, processes them with AI, and returns a filled PDF."""
    
    form_path = os.path.join(UPLOAD_FOLDER, form_file.filename)
    with open(form_path, "wb") as buffer:
        shutil.copyfileobj(form_file.file, buffer)

    receipt_paths = []
    for receipt_file in receipt_files:
        receipt_path = os.path.join(UPLOAD_FOLDER, receipt_file.filename)
        with open(receipt_path, "wb") as buffer:
            shutil.copyfileobj(receipt_file.file, buffer)
        receipt_paths.append(receipt_path)

    # Process reimbursement form
    pdf_path = process_reimbursement_form(form_path, receipt_paths, model_name)

    if not pdf_path:
        return {"error": "Failed to generate PDF"}

    return {"message": "Files processed successfully", "pdf_url": f"/download/{os.path.basename(pdf_path)}"}

@app.get("/download")
async def download_file():
    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output"
    logger.info(f"Files in output folder: {os.listdir(OP_FOLDER)}")
    #logger.info(f"Downloading file: {filename}")
    file_path = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.docx")
    logger.info(f"Downloading file: {file_path}")
    if os.path.exists(file_path):
        return FileResponse(file_path, 
                            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                            filename="Filled_Reimbursement_Form.docx")
    # mediatype for word = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    # for pdf = "application/pdf"
    return {"error": "File not found"}
