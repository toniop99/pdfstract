from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os
import tempfile
import asyncio
from pathlib import Path
import logging

# Import conversion libraries
try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None

try:
    from markitdown import MarkItDown
except ImportError:
    MarkItDown = None

try:
    from marker.converters.pdf import PdfConverter  # type: ignore
    from marker.models import create_model_dict  # type: ignore
    from marker.output import text_from_rendered  # type: ignore
    marker_available = True
except ImportError:
    PdfConverter = None
    create_model_dict = None
    text_from_rendered = None
    marker_available = False

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    DocumentConverter = None

app = FastAPI(title="PDF to Markdown Converter", description="Convert PDF files to Markdown using various libraries")

# Create templates directory
templates = Jinja2Templates(directory="templates")

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/libraries")
async def get_available_libraries():
    """Get list of available conversion libraries"""
    libraries = []
    
    if pymupdf4llm:
        libraries.append({"name": "pymupdf4llm", "available": True})
    else:
        libraries.append({"name": "pymupdf4llm", "available": False})
    
    if MarkItDown:
        libraries.append({"name": "markitdown", "available": True})
    else:
        libraries.append({"name": "markitdown", "available": False})
    
    if marker_available:
        libraries.append({"name": "marker", "available": True})
    else:
        libraries.append({"name": "marker", "available": False})
    
    if DocumentConverter:
        libraries.append({"name": "docling", "available": True})
    else:
        libraries.append({"name": "docling", "available": False})
    
    return {"libraries": libraries}

async def convert_with_pymupdf4llm(file_path: str) -> str:
    """Convert PDF using pymupdf4llm"""
    if not pymupdf4llm:
        raise HTTPException(status_code=400, detail="pymupdf4llm is not available")
    
    try:
        md_text = pymupdf4llm.to_markdown(file_path)
        return md_text
    except Exception as e:
        logger.error(f"Error with pymupdf4llm: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

async def convert_with_markitdown(file_path: str) -> str:
    """Convert PDF using markitdown"""
    if not MarkItDown:
        raise HTTPException(status_code=400, detail="markitdown is not available")
    
    try:
        md = MarkItDown()
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        logger.error(f"Error with markitdown: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

async def convert_with_marker(file_path: str) -> str:
    """Convert PDF using marker"""
    if not marker_available:
        raise HTTPException(status_code=400, detail="marker is not available")
    
    try:
        # Initialize converter with models (this might take a while on first run)
        converter = PdfConverter(  # type: ignore
            artifact_dict=create_model_dict(),  # type: ignore
        )
        # Convert PDF
        rendered = converter(file_path)
        # Extract text from rendered output
        text, _, images = text_from_rendered(rendered)  # type: ignore
        return text
    except Exception as e:
        logger.error(f"Error with marker: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

async def convert_with_docling(file_path: str) -> str:
    """Convert PDF using docling"""
    if not DocumentConverter:
        raise HTTPException(status_code=400, detail="docling is not available")
    
    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        return result.document.export_to_markdown()
    except Exception as e:
        logger.error(f"Error with docling: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

@app.post("/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    library: str = Form(...)
):
    """Convert PDF to Markdown using specified library"""
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Convert based on selected library
        if library == "pymupdf4llm":
            markdown_content = await convert_with_pymupdf4llm(temp_file_path)
        elif library == "markitdown":
            markdown_content = await convert_with_markitdown(temp_file_path)
        elif library == "marker":
            markdown_content = await convert_with_marker(temp_file_path)
        elif library == "docling":
            markdown_content = await convert_with_docling(temp_file_path)
        else:
            raise HTTPException(status_code=400, detail="Invalid library specified")
        
        return JSONResponse({
            "success": True,
            "markdown": markdown_content,
            "library_used": library,
            "filename": file.filename
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 