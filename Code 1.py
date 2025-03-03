# query = f"""
# You are an AI trained to process reimbursement forms.
# Given the extracted reimbursement form:
# {reimbursement_form_text}

# And the following parsed bill data:
# {bills_data}
# **Instruction for Extracting Reimbursement Data:**

# You are provided with an expense reimbursement form in PDF format. Your task is to **extract only the relevant details** from the form and present them in a structured format. **Do not include any additional text or explanations.**  

# Follow these rules strictly:  
# - Extract only the relevant fields from the document.  
# - If a field is missing or not applicable, write **N/A**.  
# - For numerical fields requiring summation across multiple entries, missing values should be treated as **0**.  
# - Maintain the exact structure and format in your output.  

# Return the extracted data **exactly** in the format of the form provided, adjusting accordingly to the number of receipts and expenses listed.
# Identify the required fields in the form and intelligently fill them with relevant values from the bills.
# Ensure correctness in categorizing expenditure.
# Return only structured output in a way that can be easily inserted back into the form.
# """

import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import fitz  # pymupdf
import easyocr  # Using easyOCR instead of Tesseract
from ollama import chat

def extract_text_from_pdf(pdf_path):
    """Extracts text from a given PDF file. If standard extraction fails, uses OCR."""
    try:
        print(f"[DEBUG] Extracting text from PDF: {pdf_path}")
        if not os.path.exists(pdf_path):
            print(f"Warning: File not found - {pdf_path}")
            return "[File Not Found]"
        
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
        
        if text.strip():
            print(f"[DEBUG] Standard text extraction successful for {pdf_path}")
            return text.strip()
        else:
            print(f"[DEBUG] Standard text extraction failed. Attempting OCR on {pdf_path}")
            return extract_text_using_ocr(pdf_path)
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return extract_text_using_ocr(pdf_path)

def extract_text_using_ocr(pdf_path):
    """Uses OCR to extract text from a scanned PDF using pymupdf and easyOCR."""
    try:
        print(f"[DEBUG] Performing OCR on {pdf_path} using pymupdf and easyOCR")
        reader = easyocr.Reader(['en'])  # Load OCR model for English
        doc = fitz.open(pdf_path)  # Open PDF
        text = ""
        
        for page_num in range(len(doc)):
            pix = doc[page_num].get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            extracted_text = reader.readtext(img, detail=0)  # Get extracted text
            text += "\n".join(extracted_text) + "\n"
        
        print(f"[DEBUG] OCR extraction completed for {pdf_path}")
        return text.strip() if text else "[OCR Extraction Failed]"
    except Exception as e:
        print(f"Error performing OCR on {pdf_path}: {e}")
        return "[OCR Processing Failed]"

def parse_bills(bill_pdfs):
    """Extracts text from multiple bill PDFs, using OCR if necessary."""
    print("[DEBUG] Parsing bill PDFs...")
    bills_data = []
    for bill in bill_pdfs:
        print(f"[DEBUG] Processing bill: {bill}")
        bill_text = extract_text_from_pdf(bill)
        print(f"[DEBUG] Extracted bill text:\n{bill_text}")
        bills_data.append(bill_text)
    print("[DEBUG] Bill parsing completed.")
    return bills_data

def process_data_with_ai(reimbursement_form_text, bills_data):
    print("[DEBUG] Sending data to AI for processing...")
    query = f"""
    You are an AI trained to process reimbursement forms.
    Given the extracted reimbursement form:
    {reimbursement_form_text}

    And the following parsed bill data:
    {bills_data}
    **Instruction for Extracting Reimbursement Data:**

    You are provided with an expense reimbursement form in PDF format. Your task is to **extract only the relevant details** from the form and present them in a structured format. **Do not include any additional text or explanations.**  

    Follow these rules strictly:  
    - Extract only the relevant fields from the document.  
    - If a field is missing or not applicable, write **N/A**.  
    - For numerical fields requiring summation across multiple entries, missing values should be treated as **0**.  
    - Maintain the exact structure and format in your output.  

    Return the extracted data **exactly** in the format of the form provided, adjusting accordingly to the number of receipts and expenses listed.
    Identify the required fields in the form and intelligently fill them with relevant values from the bills.
    Ensure correctness in categorizing expenditure.
    Return only structured output in a way that can be easily inserted back into the form. Make sure you give the output
    adhering to the exact format of bill data
    """
    try:
        response = chat(
            model="llama3:latest",
            messages=[{"role": "user", "content": query}]
        )
        return response['message']['content']
    except Exception as e:
        print(f"Error processing AI request: {e}")
        return "[AI Processing Failed]"

def generate_filled_form(original_form_pdf, filled_data):
    """Generates a filled reimbursement form based on AI-processed data."""
    try:
        print(f"[DEBUG] Generating filled form for: {original_form_pdf}")
        if not os.path.exists(original_form_pdf):
            print(f"Error: Original form PDF not found: {original_form_pdf}")
            return
        
        reader = PdfReader(original_form_pdf)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        output_pdf = "Filled_Reimbursement_Form.pdf"
        with open(output_pdf, "wb") as f:
            writer.write(f)

        c = canvas.Canvas(output_pdf, pagesize=letter)
        y_position = 700
        print("[DEBUG] Writing data to PDF:")
        for line in filled_data.split("\n"):
            print(line)
            c.drawString(100, y_position, line)
            y_position -= 20
        
        c.save()
        print(f"[DEBUG] Form successfully filled and saved as {output_pdf}")
    except Exception as e:
        print(f"Error generating filled form: {e}")

def main():
    """Main function to handle user input and execute the reimbursement processing pipeline."""
    print("[DEBUG] Starting reimbursement processing...")
    reimbursement_form_pdf = input("Enter reimbursement form PDF filename: ")
    if not os.path.exists(reimbursement_form_pdf):
        print("Error: Reimbursement form PDF not found!")
        return
    
    while True:
        num_bills = input("Enter the number of bills: ")
        if num_bills.isdigit() and int(num_bills) > 0:
            num_bills = int(num_bills)
            break
        else:
            print("Warning: Number of bills must be a positive integer.")
    
    bill_pdfs = []
    for i in range(num_bills):
        bill_filename = input(f"Enter bill {i+1} filename: ")
        if not os.path.exists(bill_filename):
            print(f"Warning: Bill PDF not found - {bill_filename}. Skipping...")
            continue
        bill_pdfs.append(bill_filename)

    print("[DEBUG] Extracting form text...")
    if reimbursement_form_pdf[-3:] == "txt":
        with open(reimbursement_form_pdf, "r") as file:
            form_text = file.read()
    elif reimbursement_form_pdf[-3:] == "pdf":
        form_text = extract_text_from_pdf(reimbursement_form_pdf)
    else:
        print("Error: Unsupported file format for reimbursement form.")
        return
    print(f"[DEBUG] Extracted form text:\n{form_text}")
    print("[DEBUG] Extracting bills text...")
    bills_data = parse_bills(bill_pdfs)
    
    print("[DEBUG] Processing AI-generated reimbursement data...")
    filled_data = process_data_with_ai(form_text, bills_data)
    print(f"[DEBUG] AI-generated reimbursement data:\n{filled_data}")
    file_path = "Filled_reimbursement_form.tex"
    with open(file_path, "w") as file:
        file.write(filled_data)

    print(f"LaTeX file saved as {file_path}")    
    print("[DEBUG] Generating the final filled form...")
    generate_filled_form(reimbursement_form_pdf, filled_data)
    print("[DEBUG] Process completed successfully.")

if __name__ == "__main__":
    main()
