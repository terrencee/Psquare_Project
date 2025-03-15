from fastapi import FastAPI, File, UploadFile, Form, Depends, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
#handling multiple files
from typing import List
import shutil
import os
import logging
# importing my method that will process the forms.
from file_processor import process_reimbursement_form

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

#enable cors
app.add_middleware( 
    CORSMiddleware,

    allow_origins=["*"],# for production = *. for local we could keep it as "http://localhost:3000"
    #allow requests from react frontend
        allow_credentials = True,
        allow_methods=["*"],
        allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create folder if it does not exist 

OUTPUT_FOLDER = "output" # folder to store the generated PDFs
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.post("/upload")
async def upload_files(
                      request: Request, # to inspect the request
                      form_file: UploadFile = File(...),
                      receipt_files: List[UploadFile] = File(...), # accept multiple files
                      model_name: str = Form("mistral") # we may allow frontend to select model                     
                      ):

    """ Recieves form + multiple receipts, 
    processes them with AI and 
    returns a filled form PDF URL"""
    
    # to debug : print recieved received request data
    form_data = await request.form
    logger.info(f"Received form data: {form_data}")


    # printing individual files received
    logger.info(f"Received form file: {form_file.filename}")
    logger.info(f"Received receipt files: {[file.filename for file in receipt_files]}")

    # save the form file
    form_path = os.path.join(UPLOAD_FOLDER,form_file.filename)
    with open(form_path, "wb") as buffer:
        shutil.copyfileobj(form_file.file, buffer)


    # save multiple receipts
    receipt_paths = []
    for receipt_file in receipt_files:
        receipt_path =  os.path.join(UPLOAD_FOLDER,receipt_file.filename)
        with open(receipt_path, "wb") as buffer:
            shutil.copyfileobj(receipt_file.file, buffer)
            receipt_paths.append(receipt_path)
    
    # call file processing method
    pdf_url = process_reimbursement_form(form_path, receipt_paths, model_name)

    if not pdf_url:
        return {"error": "Failed to generate PDF"}
    
    logger.info(f"Generated PDF URL: {pdf_url}")

    return {"message": "Files processed successfully", 
            "pdf_url": pdf_url}

@app.get("/download/{filename}")
async def download_file(filename: str):
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path, media_type="application/pdf", filename=filename)
        return {"error": "File not found"}

    

   

