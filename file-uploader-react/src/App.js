import React, { useState, useEffect } from "react";
//import { LatexEditor } from "@evyu/latex-editor";

function App() {
  // State for storing form and receipts
  const [formFile, setFormFile] = useState(null);
  const [receiptFiles, setReceiptFiles] = useState([]);

  // State for displaying upload success/failure messages
  const [message, setMessage] = useState("");

  // State for LLM model selection
  const [selectedModel, setSelectedModel] = useState("mistral");

  // State for storing the final generated PDF URL
  const [pdfUrl, setPdfUrl] = useState("");

  // Available models
  const models = [
    "llama3-gradient:8b", "llama2:7b", "llama2-uncensored:latest",
    "llama3-gradient:1048k", "qwen:0.5b", "qwen2:0.5b", "qwen2:1.5b",
    "llama3.2:1b", "llama2:latest", "llama2:13b", "deepseek-v2:latest",
    "llama3-chatqa:latest", "deepseek-r1:7b", "qwen2.5:1.5b", "deepseek-r1:1.5b",
    "qwen2.5:0.5b", "qwen:4b", "qwen:1.8b", "mistral-small:24b", "codestral:latest",
    "mistral-small:22b", "mistral-nemo:latest", "dolphin-mistral:latest",
    "samantha-mistral:latest", "mistral:latest", "mistrallite:latest", "phi:latest",
    "qwen2.5:14b", "qwen:14b", "qwen2.5:7b", "qwen2.5:latest", "qwen2:7b",
    "qwen:7b", "deepseek-r1:14b", "deepseek-r1:8b", "llama3.1:latest",
    "llama3:latest", "llama3.2:latest"
  ];

  // Handles Form File selection
  const handleFormFileChange = (event) => {
    setFormFile(event.target.files[0]);
    setMessage(""); // Clear previous messages
  };

  // Handles Receipt Files selection (multiple files)
  const handleReceiptFilesChange = (event) => {
    const filesArray = Array.from(event.target.files);
    setReceiptFiles(filesArray);
    setMessage(""); // Clear previous messages
  };

  // Handles file upload to the FastAPI backend
  const handleUpload = async () => {
    if (!formFile || receiptFiles.length === 0) {
      setMessage("Please upload both the form and at least one receipt!");
      return;
    }

    

    // Creating a FormData object
    const formData = new FormData();
    formData.append("form_file", formFile);
    receiptFiles.forEach((file) => formData.append("receipt_files", file));
    formData.append("model_name", selectedModel);
    console.log("Form Data:", formData.get.receiptFiles, formData.get.formFile); // Log FormData object

    try {
      // Sending a POST request to FastAPI backend
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      // Parsing the response
      const data = await response.json();
      console.log("Backend response:", data); // Log backend response

      if (data.pdf_url) {
        setPdfUrl(data.pdf_url); // Update state with final PDF URL
      }

      setMessage(data.message); // Show success message from backend
    } catch (error) {
      setMessage("Upload failed! Please try again.");
    }
  };

  // Log pdfUrl whenever it updates
  useEffect(() => {
    console.log("Updated PDF URL:", pdfUrl);
  }, [pdfUrl]);

  // download function

  const handleDownload = async () => {
    try {
        // Make a GET request to the download endpoint with the full file path as a parameter
        const response = await fetch(`http://localhost:8000/show-latex`);
        console.log("response", response);
        
        if (!response.ok) {
            throw new Error('Failed to download file');
        }
        
        // Create a blob from the response
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        // Create a temporary link and trigger download
        
        window.open(url, '_blank');
        //window.open(`https://www.sejda.com/pdf-editor?url=${encodeURIComponent(url)}`, '_blank');
      

        /*const link = document.createElement('a');
        link.href = url;
        //link.setAttribute('download', filePath.split('\\').pop()); // Handling Windows file paths
        console.log("link", link);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);*/
    } catch (error) {
        console.error('Error downloading file:', error);
    }
};

// latex component

{/*
const LatexEditorComponent = () => {
  const [latexContent, setLatexContent] = useState("");

  useEffect(() => {
      // Fetch the LaTeX content from the backend
      fetch("http://localhost:8000/get-latex")
          .then((res) => res.json())
          .then((data) => setLatexContent(data.content))  
          .catch((err) => console.error("Error fetching LaTeX file:", err));
  }, []);

  const handleSaveAndConvert = async () => {
      // Send edited LaTeX content to backend for saving and PDF conversion
      const response = await fetch("http://localhost:8000/save-latex", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ latex_content: latexContent }),
      });
      
      const data = await response.json();
      if (data.pdf_url) {
          window.open(`http://localhost:8000${data.pdf_url}`, "_blank");
      } else {
          alert("Error converting to PDF");
      }
  }
}; */}


  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>Form Processor</h2>

      {/* Form Upload */}
      <p>Upload Form:</p>
      <input type="file" onChange={handleFormFileChange} />

      {/* Multiple Receipts Upload */}
      <p>Upload The Assisting Receipts:</p>
      <input type="file" multiple onChange={handleReceiptFilesChange} />

      {/* Model Selection Dropdown */}
      <p>Select Your Preferred Model:</p>
      <select onChange={(e) => setSelectedModel(e.target.value)} value={selectedModel}>
        {models.map((model, index) => (
          <option key={index} value={model}>
            {model}
          </option>
        ))}
      </select>

      {/* Display Selected Files */}
      {formFile && <p><strong>Form Selected:</strong> {formFile.name}</p>}
      {receiptFiles.length > 0 && (
        <div>
          <strong>Receipts Selected:</strong>
          <ul>
            {receiptFiles.map((file, index) => (
              <li key={index}>{file.name}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        style={{
          marginTop: "15px",
          padding: "10px",
          backgroundColor: "blue",
          color: "white",
          cursor: "pointer",
          border: "none",
          borderRadius: "5px",
        }}
      >
        Process Form
      </button>

      {/* Show Upload Status Message */}
      {message && <p style={{ color: "red", marginTop: "10px" }}>{message}</p>}

      {/* Download Button (always visible, but disabled until pdf is ready) */}
      <div style={{ marginTop: "20px" }}>
        <p><strong>Download Filled Form:</strong></p>

<button
  disabled={!pdfUrl}
  onClick={() => pdfUrl && handleDownload(pdfUrl)}
  style={{
    padding: "10px",
    backgroundColor: pdfUrl ? "green" : "gray",
    color: "white",
    cursor: pdfUrl ? "pointer" : "not-allowed",
    border: "none",
    borderRadius: "5px",
  }}
>
  Download Form
</button>

        {/* Show PDF URL if available */}
        {pdfUrl && (
          <p style={{ marginTop: "10px", wordBreak: "break-word" }}>
            <strong>Generated PDF URL:</strong>{" "}
            <a href={`http://localhost:8000${pdfUrl}`} target="_blank" rel="noopener noreferrer">{`http://localhost:8080${pdfUrl}`}
            </a>
          </p>
        )}
      </div>
      {/*}
      <div>
            <h2>LaTeX Editor</h2>
            <LatexEditor value={latexContent} onChange={setLatexContent} />
            <button onClick={handleSaveAndConvert}>Download as PDF</button>
        </div> */}
      {/* Show Success or Failure Messages */}
      {message && <p style={{ marginTop: "10px", fontWeight: "bold" }}>{message}</p>}
    </div>
  );
}

export default App;
