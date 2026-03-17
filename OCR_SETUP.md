# OCR Setup Guide - Scanned PDF Support

## Problem Fixed ✓

Your Bank LLM system now supports **scanned (image-only) PDFs** through Optical Character Recognition (OCR). Previously, PDFs like `uploads_OM_9_AGVB_Lending_Policy_2023.pdf` couldn't be processed if they were scanned documents.

## How It Works

The document ingestion pipeline now has 3 fallback methods:

1. **PyPDF** - Direct text extraction (fastest, works with native PDFs)
2. **PDFMiner** - Alternative text extraction (handles complex layouts)
3. **OCR (Tesseract)** - Image-to-text conversion (handles scanned PDFs) ← *NEW*

If the first two methods extract less than 50 characters, OCR is automatically triggered.

## Installation Steps

### 1. **Install Tesseract-OCR** (One-time setup)

Tesseract-OCR must be installed as a **system application** (not just a Python package).

#### For Windows:

1. Download the installer from:
   ```
   https://github.com/UB-Mannheim/tesseract/wiki
   ```
   Look for: **`tesseract-ocr-w64-setup-v5.x.x.exe`**

2. Run the installer and use **default installation path**:
   ```
   C:\Program Files\Tesseract-OCR
   ```

3. Verify installation by opening PowerShell and running:
   ```powershell
   & 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
   ```
   You should see version information.

### 2. **Install Python Packages**

Run the updated `setup.bat` or manually install:

```bash
cd backend
pip install -r requirements.txt
```

New packages added:
- `pytesseract` - Python interface to Tesseract
- `pdf2image` - Convert PDF pages to images
- `Pillow` - Image processing

## Testing

Once installed, try uploading a scanned PDF through the web interface. You should see in the logs:

```
[12:33:44 pm] Folder ingestion: Found 1 files. Ingestion started in background.
[12:33:45 pm] Attempting OCR extraction for file.pdf...
[12:33:46 pm] OCR extraction yielded 5432 chars for file.pdf...
[12:33:46 pm] ✓ Successfully ingested file.pdf (23 chunks)
```

## Troubleshooting

### Error: "pytesseract.TesseractNotFoundError"
- **Cause**: Tesseract-OCR not installed or wrong path
- **Fix**: 
  - Verify installation: `"C:\Program Files\Tesseract-OCR\tesseract.exe"` exists
  - Restart Python/the server after installing Tesseract
  - If installed elsewhere, edit `backend/document_processor.py` line 20:
    ```python
    pytesseract.pytesseract.pytesseract_cmd = r'YOUR_TESSERACT_PATH'
    ```

### Error: "ModuleNotFoundError: No module named 'pdf2image'"
- **Cause**: Requirements not installed
- **Fix**: Run `pip install pdf2image pytesseract Pillow`

### OCR is slow
- **Expected**: OCR takes 5-30 seconds per page (depending on image quality/size)
- Use native PDFs when possible (faster)

### Very low OCR accuracy
- **Cause**: Poor PDF image quality or unusual fonts
- **Options**:
  - Try uploading a higher-quality scan
  - Manually pre-process the PDF using a tool like Adobe Acrobat

## Performance Notes

- **Native PDFs**: ~100ms to extract
- **PDFMiner fallback**: ~200ms per page
- **OCR**: ~3-10 seconds per page (depending on image complexity)

OCR is only triggered if native extraction fails, so performance is optimized.

## System Requirements

- **RAM**: At least 2GB free (OCR can use 500MB per page)
- **Disk**: ~100MB for Tesseract-OCR installation
- **Python**: 3.8+

## Related Files Modified

- `backend/document_processor.py` - Added OCR fallback
- `backend/requirements.txt` - Added OCR dependencies
- `setup.bat` - Added Tesseract setup instructions

---

**Need help?** Check the main README.md or review the logs in the web interface.
