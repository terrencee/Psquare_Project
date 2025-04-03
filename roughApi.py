import base64
import io
import os
import cv2
import numpy as np
import fitz  # PyMuPDF for PDFs
import pdfplumber
from PIL import Image
from paddleocr import PaddleOCR  # Optimized OCR
from multiprocessing import Pool, cpu_count
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from bs4 import BeautifulSoup
from docx import Document
import docx2txt
from dotenv import load_dotenv  
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import subprocess
from fastapi.responses import HTMLResponse
import io
from fastapi.responses import StreamingResponse
import subprocess
import logging
from typing import List

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ocr = PaddleOCR(use_angle_cls=True, lang="en")  # Load PaddleOCR once

# Image Preprocessing for Better OCR Performance
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    return thresh

# Function to Extract Text from an Image
def ocr_image(image_bytes):
    image = np.array(Image.open(io.BytesIO(image_bytes)))
    processed_img = preprocess_image(image)
    result = ocr.ocr(processed_img, cls=True)
    extracted_text = " ".join([line[1][0] for page in result for line in page if line[1]])
    return extracted_text

# Extract Text from PDFs Efficiently
def extract_text_from_pdf(pdf_bytes):
    text_results = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        num_pages = len(pdf.pages)
        with Pool(processes=min(cpu_count(), num_pages)) as pool:
            text_results = pool.map(ocr_image, [page.to_image().original.convert("RGB") for page in pdf.pages])
    return " ".join(text_results)

# Extract Text from Word Documents
def extract_text_from_docx(docx_bytes):
    with io.BytesIO(docx_bytes) as doc_file:
        text = docx2txt.process(doc_file)
    return text

# Convert HTML to Editable HTML
def convert_html_to_editable(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Make all input fields editable
    for tag in soup.find_all(["input", "textarea"]):
        tag["contenteditable"] = "true"
    
    # Wrap everything inside a simple editor
    editable_html = f"""
    <html>
    <head>
        <title>Editable Form</title>
        <script>
            function saveForm() {{
                alert('Form saved! Implement backend save functionality.');
            }}
        </script>
    </head>
    <body>
        {str(soup)}
        <button onclick="saveForm()">Save Form</button>
    </body>
    </html>
    """
    return editable_html

@app.post("/process_file/")
async def process_file(file: UploadFile = File(...)):
    file_bytes = await file.read()
    
    if file.content_type == "application/pdf":
        extracted_text = extract_text_from_pdf(file_bytes)
        return JSONResponse(content={"text": extracted_text})
    
    elif "image" in file.content_type:
        extracted_text = ocr_image(file_bytes)
        return JSONResponse(content={"text": extracted_text})

    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        extracted_text = extract_text_from_docx(file_bytes)
        editable_html = f"<textarea style='width:100%;height:500px;'>{extracted_text}</textarea>"
        return HTMLResponse(content=editable_html)

    elif file.content_type == "text/html":
        editable_html = convert_html_to_editable(file_bytes.decode("utf-8"))
        return HTMLResponse(content=editable_html)

    else:
        return JSONResponse(content={"error": "Unsupported file type"}, status_code=400)
