import { useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import html2pdf from "html2pdf.js";

const PreviewPage = () => {
  const location = useLocation();

     // Load form HTML from localStorage
  //const storedHtml = localStorage.getItem("previewFormHtml");
  //const storedFields = localStorage.getItem("extractedFields");
  const queryParams = new URLSearchParams(location.search);
  const formHtmlFromURL = queryParams.get("formHtml");


 
  //const { formHtml, extractedFields } = location.state || {}; // Get data from navigation

    // Maintain the editable form state
    //const [editableForm, setEditableForm] = useState(storedHtml || "<p>No form available</p>");
    const [editableForm, setEditableForm] = useState(
    formHtmlFromURL ? decodeURIComponent(formHtmlFromURL) : "<p>Loading form...</p>"
    );
    const [extractedFields, setExtractedFields] = useState(null);
    //const extractedFields = storedFields ? JSON.parse(storedFields) : null;
  //const [editableForm, setEditableForm] = useState(formHtml || "<p>No form available</p>");
  const [showDownloadButton, setShowDownloadButton] = useState(false);


  // (1) Read from localStorage in case postMessage fails
  useEffect(() => {
    if (!formHtmlFromURL) {
      const storedHtml = localStorage.getItem("previewFormHtml");
      if (storedHtml) {
        setEditableForm(storedHtml);
      }
    }
  }, [formHtmlFromURL]);


  useEffect(() => {
    // (2) Listen for the message from the upload page
    const receiveMessage = (event) => {
      console.log("Received message in PreviewPage:", event.data); // Debug log
      if (event.origin !== window.origin){
        console.warn("Blocked message from untrusted origin:", event.origin);
        return; // Ensure it's from the same origin
      } 
      if (event.data.filledHtml) {
        console.log("Updating editableForm with filledHtml");
        setEditableForm(event.data.filledHtml); // Set the filled form dynamically
        setShowDownloadButton(true); // Show download button after update
      }
      if (event.data.extractedFields) {
        console.log("Updating extractedFields with received data");
        setExtractedFields(event.data.extractedFields);
      }
    };

    window.addEventListener("message", receiveMessage);

    return () => {
      window.removeEventListener("message", receiveMessage);
    };
  }, []);


  /*
  useEffect(() => {
    if (extractedFields && editableForm) {
      let updatedHtml = editableForm;  // Use the existing form structure  

      // Loop through extractedFields and fill form inputs dynamically
      Object.entries(extractedFields).forEach(([fieldId, fieldValue]) => {
        updatedHtml = updatedHtml.replace(
          new RegExp(`id=["']${fieldId}["'][^>]*value=["'][^"']*["']`, "g"),
          `id="${fieldId}" value="${fieldValue}"`
        );
      });

      setEditableForm(updatedHtml); // Update only the field values
    }
  }, [extractedFields]);  // Only run when extracted data is received
  */

  // 3 Update form when extracted fields are received
  useEffect(() => {
    if (extractedFields && editableForm) {
      let updatedHtml = editableForm;
      Object.entries(extractedFields).forEach(([fieldId, fieldValue]) => {
        updatedHtml = updatedHtml.replace(
          new RegExp(`id=["']${fieldId}["'][^>]*value=["'][^"']*["']`, "g"),
          `id="${fieldId}" value="${fieldValue}"`
        );
      });

      //setEditableForm(updatedHtml);
      // Force a state update
    setEditableForm("");
    setTimeout(() => setEditableForm(updatedHtml), 50);
    }
  }, [extractedFields]);


  //  Function to Download as PDF
  const handleDownloadPDF = () => {
    const content = document.getElementById("preview-content");
    html2pdf()
      .from(content)
      .save("filled-form.pdf");
  };

  return (
    <div>
      <div id="preview-content" dangerouslySetInnerHTML={{ __html: editableForm }}></div>

      {showDownloadButton && (
        <button onClick={handleDownloadPDF} style={{ marginTop: "20px", padding: "10px", fontSize: "16px" }}>
          Download as PDF
        </button>
      )}
    </div>
  );
};

export default PreviewPage;
