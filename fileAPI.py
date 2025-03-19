from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import FileResponse
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

def extract_readable_text(tex_content):
    """Convert LaTeX to readable text, preserving tables and images."""
    tex_content = re.sub(r"\\section\*?\{(.*?)\}", r"<h2>\1</h2>", tex_content)  # Convert sections to headers
    tex_content = re.sub(r"\\textbf\{(.*?)\}", r"<b>\1</b>", tex_content)  # Convert bold text
    tex_content = re.sub(r"\\textit\{(.*?)\}", r"<i>\1</i>", tex_content)  # Convert italic text

    # Handle LaTeX tables
    tex_content = re.sub(r"\\begin\{tabular\}(.*?)\\end\{tabular\}", "<table border='1'><tr><td>[Table Placeholder]</td></tr></table>", tex_content, flags=re.DOTALL)

    # Handle images (\includegraphics)
    tex_content = re.sub(r"\\includegraphics\[.*?\]\{(.*?)\}", r"<img src='\1' width='300px' alt='Image'>", tex_content)

    return tex_content.replace("\n", "<br>")  # Preserve line breaks

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

###

@app.post("/save-latex")
async def save_latex(data: dict):
    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output"
    TEX_FILE_PATH = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.tex")
    PDF_FILE_PATH = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.pdf")
    pdflatex_path = r"C:\Users\chick\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
    """Save edited content and convert to PDF."""
    edited_text = data.get("edited_text", "")
    if not edited_text:
        return {"error": "No content received"}

    # Convert back to LaTeX (basic version, can be improved)
    tex_content = edited_text.replace("<br>", "\n")
    tex_content = re.sub(r"<h2>(.*?)</h2>", r"\\section{\1}", tex_content)
    tex_content = re.sub(r"<b>(.*?)</b>", r"\\textbf{\1}", tex_content)
    tex_content = re.sub(r"<i>(.*?)</i>", r"\\textit{\1}", tex_content)
    tex_content = re.sub(r"<table.*?>.*?</table>", r"\\begin{tabular}{c c c} Placeholder Table \\end{tabular}", tex_content)

    with open(TEX_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(tex_content)

    # Convert to PDF
    subprocess.run([pdflatex_path, "-output-directory", OP_FOLDER, TEX_FILE_PATH], cwd=OP_FOLDER)

    if not os.path.exists(PDF_FILE_PATH):
        return {"error": "PDF conversion failed"}

    return {"pdf_url": "/download-edited-pdf"}

###

@app.get("/download-edited-pdf")
async def download_edited_pdf():
    OP_FOLDER = r"D:\Making LLMs fill Reimbursement form\output"
    TEX_FILE_PATH = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.tex")
    PDF_FILE_PATH = os.path.join(OP_FOLDER, "Filled_Reimbursement_Form.pdf")
    """Serve the converted PDF."""
    if os.path.exists(PDF_FILE_PATH):
        return FileResponse(PDF_FILE_PATH, media_type="application/pdf", filename="Edited_Reimbursement_Form.pdf")
    return {"error": "File not found"}



