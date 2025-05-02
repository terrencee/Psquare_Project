import { useLocation } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import html2pdf from "html2pdf.js";

const PreviewPage = () => {
  const location = useLocation();

     // Load form HTML from localStorage
  //const storedHtml = localStorage.getItem("previewFormHtml");
  //const storedFields = localStorage.getItem("extractedFields");
  const queryParams = new URLSearchParams(location.search);
  const formHtmlFromURL = queryParams.get("formHtml");
  const previewRef = useRef(null);

 
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

        // Save to localStorage for persistence
        localStorage.setItem("previewFormHtml", event.data.filledHtml);
      }
      if (event.data.extractedFields) {
        console.log("Updating extractedFields with received data");
        setExtractedFields(event.data.extractedFields);

        // Optional: Save to localStorage
        localStorage.setItem("extractedFields", JSON.stringify(event.data.extractedFields));
      }
    };

    window.addEventListener("message", receiveMessage);

    return () => {
      // Clean up to prevent memory leaks
      window.removeEventListener("message", receiveMessage);
    };
  }, []);


  // (3) Dynamic JS (Row Add/Remove, Date Auto-Fill)
  useEffect(() => {
    if (editableForm) {
      setTimeout(() => {
        window.addRow = function () {
          const table = document.getElementById("cash-memo-table").getElementsByTagName('tbody')[0];
          const rowCount = table.rows.length + 1;
          const row = table.insertRow(-1);
          row.innerHTML = `
              <td>${rowCount}</td>
              <td><input type="text" name="cash_memo_no_${rowCount}" /></td>
              <td><input type="date" name="cash_memo_date_${rowCount}" /></td>
              <td><input type="text" name="firm_name_${rowCount}" /></td>
              <td><input type="number" name="amount_${rowCount}" step="0.01" /></td>
              <td><button type="button" class="remove-row-btn" onclick="removeRow(this)">Remove</button></td>
          `;
          const today = new Date().toISOString().split('T')[0];
          row.querySelector('input[type="date"]').value = today;
        };
  
        window.removeRow = function (button) {
          const row = button.closest("tr");
          if (row && row.parentNode.rows.length > 1) {
            row.remove();
          } else {
            alert("At least one row must remain in the table.");
          }
        };
      }, 500); // slight delay to ensure DOM is rendered
    }
  }, [editableForm]);   // Trigger every time editableForm updates

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

    // Save to localStorage as backup
    localStorage.setItem("previewFormHtml", updatedHtml);
    setShowDownloadButton(true); // Show download button after update

    }
  }, [extractedFields]);


  //4  Function to Download as PDF
  const handleDownloadPDF = () => {
    const content = document.getElementById("preview-content");
    if (!content) {
      console.error("No editable form found for PDF generation");
      return;
    }
    html2pdf()
      .from(content)
     /* .set({
        margin: 10,
        filename: "form-preview.pdf",
        html2canvas: { scale: 2 },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
      })*/
      .save("filled-form.pdf");
  };

  // (5) save user edits to localStorage
  useEffect(() => {
    const handleInput = () => {
      if (previewRef.current) {
        localStorage.setItem("previewFormHtml", previewRef.current.innerHTML);
        console.log("Updated preview Saved to localStorage:", previewRef.current.innerHTML);
      }
    };
  
    const previewElement = previewRef.current;
  
    if (previewElement) {
      previewElement.addEventListener("input", handleInput);
    }
  
    return () => {
      if (previewElement) {
        previewElement.removeEventListener("input", handleInput);
      }
    };
  }, []);
  

  // (5) Handle form edits by the user
  /*const handleFormChange = (event) => {
    const updatedHtml = event.target.innerHTML;
    setEditableForm(updatedHtml);
    localStorage.setItem("previewFormHtml", updatedHtml);
  };*/

  return (
    <div>
      <h2></h2>
      <div 
        id="preview-content"
        ref = {previewRef}
       dangerouslySetInnerHTML={{ __html: editableForm }}></div>
      {/*onInput={(e) => {
        const updatedHtml = e.currentTarget.innerHTML;
        setEditableForm(updatedHtml);
        localStorage.setItem("previewFormHtml", updatedHtml);
      }}*/}

      {showDownloadButton && (
        <button onClick={handleDownloadPDF} 
        style={{
          border: "1px solid #ccc",
          padding: "16px",
          minHeight: "400px",
          marginBottom: "20px",
          backgroundColor: "#f9f9f9",
        }}
        >
          Download as PDF
        </button>
      )}
    </div>
  );
};

export default PreviewPage;
