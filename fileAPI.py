from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import subprocess
from fastapi.responses import HTMLResponse
import io
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import re
import shutil
import logging
from typing import List
import fitz  # pymupdf
import pdfplumber  # Best for extracting tables
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from file_processor import process_reimbursement_form
import pytesseract  # OCR
from PIL import Image
import json
from pdf2image import convert_from_path
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import cv2
import pdfplumber
import docx2txt
import numpy as np
from pypdf import PdfReader
import layoutparser as lp
import requests  # To send files to Ollama

# Only needed for Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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

# Path to pdflatex (ensure this is correct)
PDFLATEX_PATH = r"C:\Users\chick\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"

# ollama api url
OLLAMA_URL = "http://localhost:11434/api/generate" 

async def process_with_ollama(file_path: str):
    """ Send file to Ollama for text extraction """
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(OLLAMA_URL, files=files, json={"model": "mistral"})
    
    if response.status_code == 200:
        return response.json().get("response", "No text extracted")
    else:
        return "Error processing file with Ollama"

# Extract text & tables from an image (JPEG, PNG).
def process_image(image_path):
    """ Extract text & tables from an image (JPEG, PNG). """
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)  # OCR
    return text

# Extract text & tables from a PDF.    

def process_pdf(pdf_path):
    """ Extract text & tables from a PDF. """
    extracted_data = {"text": [], "tables": []}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            tables = page.extract_tables()
            
            if text:
                extracted_data["text"].append(text)
            if tables:
                extracted_data["tables"].extend(tables)

    return extracted_data

# Extract text from a Word document
def process_word(docx_path):
    """ Extract text from a Word document. """
    text = docx2txt.process(docx_path)
    return text


# ocr function
def extract_text_ocr(pdf_path):
    images = convert_from_path(pdf_path)
    extracted_text = [pytesseract.image_to_string(img) for img in images]
    return extracted_text

# converting html tables to latex properly
def html_table_to_latex(html_table):
    """Convert an HTML table back to LaTeX."""
    rows = re.findall(r"<tr>(.*?)</tr>", html_table, flags=re.DOTALL)
    latex_table = r"\begin{tabular}{|" + "c|" * len(rows[0].split("</td>")) + "}\hline\n"
    for row in rows:
        cells = re.findall(r"<td.*?>(.*?)</td>", row, flags=re.DOTALL)
        latex_table += " & ".join(cells) + r" \\\hline" + "\n"
    latex_table += r"\end{tabular}"
    return latex_table

# Convert LaTeX tables into HTML tables instead of placeholders
def convert_table(match):
        table_content = match.group(1)
        rows = table_content.strip().split(r"\\")
        html_table = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
        for row in rows:
            if row.strip():  # Skip empty lines
                cells = row.split("&")
                html_table += "<tr>" + "".join(f"<td contenteditable='true'>{cell.strip()}</td>" for cell in cells) + "</tr>"
        html_table += "</table><br>"
        return html_table

def extract_readable_text(tex_content):
    """Convert LaTeX to readable text, preserving tables and images."""
    tex_content = re.sub(r"\\section\*?\{(.*?)\}", r"<h2>\1</h2>", tex_content)  # Convert sections to headers
    tex_content = re.sub(r"\\textbf\{(.*?)\}", r"<b>\1</b>", tex_content)  # Convert bold text
    tex_content = re.sub(r"\\textit\{(.*?)\}", r"<i>\1</i>", tex_content)  # Convert italic text

    

    # Handle LaTeX tables
    tex_content = re.sub(r"\\begin\{tabular\}\{.*?\}(.*?)\\end\{tabular\}", convert_table, tex_content, flags=re.DOTALL)

    # Handle images (\includegraphics)
    tex_content = re.sub(r"\\includegraphics\[.*?\]\{(.*?)\}", r"<img src='\1' width='300px' alt='Image'>", tex_content)

    

    return tex_content.replace("\n", "<br>")  # Preserve line breaks

# extracting pdf pg content with pymupdf
def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    return [page.get_text("text") for page in doc]

# blank editable gui

@app.post("/preview-editable-gui")
async def preview_editable_gui(file: UploadFile = File(...)):
    """ Extract form structure using Ollama for OCR. """
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    extracted_text = await process_with_ollama(file_path)
    
    return JSONResponse(content={"text": extracted_text})

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

# editable gui after processing the form

@app.post("/generate-editable-gui")
async def generate_editable_gui(form_path: str):
    """Extracts fields from the uploaded form and generates an editable structure."""
    
    extracted_data = {}
    with pdfplumber.open(form_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            tables = page.extract_tables()

            extracted_data["text"] = text
            extracted_data["tables"] = tables

    # Extract key-value pairs using OCR for missing fields
    extracted_data["ocr_extracted"] = []
    with fitz.open(form_path) as pdf:
        for page_num in range(len(pdf)):
            pix = pdf[page_num].get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_text = pytesseract.image_to_string(img)
            extracted_data["ocr_extracted"].append(ocr_text)

    return JSONResponse(content=extracted_data)

# Download the filled PDF

@app.post("/save-latex")
async def save_latex(data: dict):
    """Generate LaTeX content dynamically from extracted fields and save as PDF."""
    tex_template = r"""
    \documentclass[12pt]{article}
    \usepackage{tabularx}
    \begin{document}

    \section*{Reimbursement Form}

    \textbf{Name:} \underline{\hspace{5cm}{{name}}} \\
    \textbf{Signature:} \underline{\hspace{5cm}{{signature}}} \\
    \textbf{Designation:} \underline{\hspace{5cm}{{designation}}} \\

    \begin{tabularx}{\textwidth}{|X|X|X|X|}
        \hline
        Voucher Number & Voucher Date & Amount & Remarks \\
        \hline
        {{table_rows}}
        \hline
    \end{tabularx}

    \end{document}
    """

    # Populate the template with user data
    filled_tex = tex_template.replace("{{name}}", data.get("name", ""))
    filled_tex = filled_tex.replace("{{signature}}", data.get("signature", ""))
    filled_tex = filled_tex.replace("{{designation}}", data.get("designation", ""))

    table_rows = "\n".join([" & ".join(row) + r" \\" for row in data.get("tables", [])])
    filled_tex = filled_tex.replace("{{table_rows}}", table_rows)

    tex_file_path = os.path.join(OUTPUT_FOLDER, "Filled_Reimbursement_Form.tex")
    pdf_file_path = os.path.join(OUTPUT_FOLDER, "Filled_Reimbursement_Form.pdf")

    with open(tex_file_path, "w", encoding="utf-8") as f:
        f.write(filled_tex)

    # Compile to PDF
    subprocess.run([PDFLATEX_PATH, "-output-directory", OUTPUT_FOLDER, tex_file_path], cwd=OUTPUT_FOLDER)

    if not os.path.exists(pdf_file_path):
        return {"error": "PDF conversion failed"}

    return {"pdf_url": "/download-edited-pdf"}

@app.get("/download-edited-pdf")
async def download_edited_pdf():
    """Serve the converted PDF."""
    pdf_file_path = os.path.join(OUTPUT_FOLDER, "Filled_Reimbursement_Form.pdf")
    if os.path.exists(pdf_file_path):
        return FileResponse(pdf_file_path, media_type="application/pdf", filename="Edited_Reimbursement_Form.pdf")
    return {"error": "File not found"}

@app.get("/download")
async def download_file():
    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output"
    logger.info(f"Files in output folder: {os.listdir(OP_FOLDER)}")
    #logger.info(f"Downloading file: {filename}")
    file_path = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.pdf")
    logger.info(f"Downloading file: {file_path}")
    if os.path.exists(file_path):
        return FileResponse(file_path, 
                            media_type="application/pdf", 
                            filename="Filled_Reimbursement_Form.pdf")
    # mediatype for word = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    # for pdf = "application/pdf"
    return {"error": "File not found"}

######################################################

@app.get("/show")
async def show_file():
    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output"
    logger.info(f"Files in output folder: {os.listdir(OP_FOLDER)}")

    #pdf_path = r"D:\Making LLMs fill Reimbursement form\output\Filled_Reimbursement_Form.pdf"
    #html_path = r"D:\Making LLMs fill Reimbursement form\output\Filled_Reimbursement_Form.html"

    #logger.info(f"Downloading file: {filename}")
    pdf_path = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.pdf")
    html_path = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.html")
    file_path = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.pdf")
    logger.info(f"Downloading file: {file_path}")
    if not os.path.exists(pdf_path):
        return {"error": "PDF not found"}
    
    # Convert PDF to HTML (USING PDF2HTMLEX)
    # subprocess.run(["pdf2htmlEX", "--zoom", "1.3", pdf_path, html_path])

    # Load the PDF
    doc = fitz.open(pdf_path)
    html_content = "<html><body>"

    # Extract tables using pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("xhtml")  # Use XHTML to preserve structure
            text = text.replace("\n", "<br>")  

            # Ensure correct page breaks when saving to PDF
            html_content += f'<h3 style="page-break-before: always;">Page {page_num}</h3>'
            html_content += f'<div contenteditable="true" style="border: 1px dashed gray; padding: 5px;">{text}</div>'

            # Extract tables
            tables = pdf.pages[page_num - 1].extract_tables()
            for table in tables:
                html_content += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
                for row in table:
                    html_content += "<tr>"
                    for cell in row:
                        html_content += f"<td contenteditable='true' style='padding: 5px;'>{cell}</td>"
                    html_content += "</tr>"
                html_content += "</table><br>"

            # Extract images and add them to HTML
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_data = base_image["image"]
                image_ext = base_image["ext"]  # Get the image format (jpeg, png)

                # Save extracted image to a temporary location
                image_filename = f"page_{page_num}_image_{img_index}.{image_ext}"
                image_path = os.path.join(OP_FOLDER, image_filename)
                with open(image_path, "wb") as f:
                    f.write(image_data)

                # Add the image to the HTML content
                html_content += f'<img src="http://localhost:8000/static/{image_filename}" style="max-width:100%;"><br>'

    # Inject JavaScript for editing and PDF saving
    html_content += """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.9.3/html2pdf.bundle.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            let paragraphs = document.querySelectorAll("div[contenteditable='true']");
            paragraphs.forEach(p => {
                p.contentEditable = "true";  // Make text editable
                p.style.border = "1px dashed gray";
                p.style.padding = "5px";
            });
        });

        function saveAsPDF() {
            html2pdf().from(document.body).save("Edited_PDF.pdf");
        }
    </script>
    
    <button onclick="saveAsPDF()" style="position: fixed; top: 10px; right: 10px; padding: 10px; background: blue; color: white; border: none; cursor: pointer;">
        Save as PDF
    </button>
    """

    html_content += "</body></html>"

    return HTMLResponse(content=html_content)

#########################################################################

@app.get("/show-latex")
async def show_latex_editor():
    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output"
    tex_file_path = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.tex")

    if not os.path.exists(tex_file_path):
        return {"error": "LaTeX file not found"}

    # Read the LaTeX file
    with open(tex_file_path, "r", encoding="utf-8") as f:
        tex_content = f.read()

    # Generate an HTML page with an embedded LaTeX editor
    html_content = f"""
    <html>
    <head>
        <title>Edit LaTeX File</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js"></script>
    </head>
    <body>
        <h2>Edit LaTeX File</h2>
        <div id="editor" style="width: 100%; height: 500px; border: 1px solid gray;">{tex_content}</div>

        <button onclick="saveAsPDF()" style="margin-top: 10px; padding: 10px; background: blue; color: white;">
            Save as PDF
        </button>

        <script>
            var editor = ace.edit("editor");
            editor.setTheme("ace/theme/monokai");
            editor.session.setMode("ace/mode/latex");

            function saveAsPDF() {{
                let latexCode = editor.getValue();
                fetch("http://localhost:8000/convert-latex-to-pdf", {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json"
                    }},
                    body: JSON.stringify({{"latex_content": latexCode}})
                }}).then(response => response.json())
                  .then(data => {{
                      if (data.pdf_url) {{
                          window.open("http://localhost:8000" + data.pdf_url, "_blank");
                      }}
                  }});
            }}
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

#########################################################################

@app.post("/convert-latex-to-pdf")
async def convert_latex_to_pdf(data: dict):
    pdflatex_path = r"C:\Users\chick\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output\edited_output"
    tex_file_path = os.path.join(OP_FOLDER, "Edited_Reimbursement_Form.tex")
    pdf_file_path = os.path.join(OP_FOLDER, "Edited_Reimbursement_Form.pdf")

    # Save the edited LaTeX content to a file
    with open(tex_file_path, "w", encoding="utf-8") as f:
        f.write(data["latex_content"])

    # Compile LaTeX to PDF using pdflatex
    subprocess.run([pdflatex_path, "-output-directory", OP_FOLDER, tex_file_path], cwd=OP_FOLDER)

    if not os.path.exists(pdf_file_path):
        return {"error": "PDF conversion failed"}

    return {"pdf_url": f"/download-edited-pdf"}


####################################################################


@app.get("/show-latex-editor")
async def show_latex_editor():

    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output"
    TEX_FILE_PATH = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.tex")
    PDF_FILE_PATH = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.pdf")
    """Serve an editable version of the LaTeX file as plain text."""
    if not os.path.exists(TEX_FILE_PATH):
        return {"error": "LaTeX file not found"}

    with open(TEX_FILE_PATH, "r", encoding="utf-8") as f:
        tex_content = f.read()

    formatted_content = extract_readable_text(tex_content)

    # Serve the HTML Editor
    html_content = f"""
    <html>
    <head>
        <title>Edit Document</title>
        <script>
            function saveAndConvert() {{
                let editedContent = document.getElementById("editor").innerHTML;
                fetch("http://localhost:8000/save-latex", {{
                    method: "POST",
                    headers: {{"Content-Type": "application/json"}},
                    body: JSON.stringify({{"edited_text": editedContent}})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.pdf_url) {{
                        window.open("http://localhost:8000" + data.pdf_url, "_blank");
                    }} else {{
                        alert("Error converting to PDF");
                    }}
                }});
            }}
        </script>
    </head>
    <body>
        <h2>Edit Your Document</h2>
        <div id="editor" contenteditable="true" style="border: 1px solid gray; padding: 10px; min-height: 300px;">{formatted_content}</div>
        <button onclick="saveAndConvert()" style="margin-top: 10px; padding: 10px; background: blue; color: white;">Download as PDF</button>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)



