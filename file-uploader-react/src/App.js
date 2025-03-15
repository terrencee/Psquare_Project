import React, { useState, useEffect } from "react";

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

  // Log `pdfUrl` whenever it updates
  useEffect(() => {
    console.log("Updated PDF URL:", pdfUrl);
  }, [pdfUrl]);

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
        Upload Files
      </button>

      {/* Show Upload Status Message */}
      {message && <p style={{ color: "red", marginTop: "10px" }}>{message}</p>}

      {/* Download Button (always visible, but disabled until pdfUrl exists) */}
      <div style={{ marginTop: "20px" }}>
        <p><strong>Download Filled Form:</strong></p>
        <button
          disabled={!pdfUrl}  // Disable if pdfUrl is empty
          style={{
            padding: "10px",
            backgroundColor: pdfUrl ? "green" : "gray",  // Change color when enabled
            color: "white",
            cursor: pdfUrl ? "pointer" : "not-allowed",  // Change cursor
            border: "none",
            borderRadius: "5px",
          }}
          onClick={() => {
            if (pdfUrl) window.open(pdfUrl, "_blank");
          }}
        >
          Download Form
        </button>

        {/* Show PDF URL if available */}
        {pdfUrl && (
          <p style={{ marginTop: "10px", wordBreak: "break-word" }}>
            <strong>Generated PDF URL:</strong>{" "}
            <a href={pdfUrl} target="_blank" rel="noopener noreferrer">
              {pdfUrl}
            </a>
          </p>
        )}
      </div>
    </div>
  );
}

export default App;
