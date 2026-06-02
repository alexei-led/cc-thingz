---
description: Extract structured data from PDF documents — text, tables, forms, and
  metadata. Use when reading or extracting content from a `.pdf` file, parsing invoices/reports/scanned
  documents, or converting PDF data to JSON/CSV. NOT for generating PDFs, and NOT
  for plain-text/markdown files (read those directly).
name: parsing-documents
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Parsing Documents (PDF Extraction)

Extract structured information from PDF documents. Try the cheapest reliable method first.

## Parsing Strategy (Priority Order)

### 1. Native Reading (when supported)

Use the runtime's native PDF reader only when it explicitly supports PDF inputs.
If the current reader supports only text/images, skip to CLI tools or page-image
conversion instead of claiming the PDF was read.

```
Read → /path/to/document.pdf  # only on runtimes with PDF support
```

### 2. CLI Tools (quick operations)

```bash
pdftotext document.pdf output.txt        # Extract text
pdftotext -layout document.pdf -         # Preserve layout
pdfinfo document.pdf                     # PDF metadata
pdftoppm -png document.pdf output        # Convert pages to images
```

### 3. Python Libraries (complex extraction)

`pdfplumber` — best for tables:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        text = page.extract_text()
```

`pypdf` — metadata and forms:

```python
from pypdf import PdfReader

reader = PdfReader("document.pdf")
metadata = reader.metadata
fields = reader.get_form_text_fields()
```

## Common Extraction Patterns

### Tables

```python
def extract_tables(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                tables.append({"page": page_num, "data": table})
    return tables
```

### Region by Bounding Box

```python
def extract_region(pdf_path, page_num, bbox):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]
        return page.crop(bbox).extract_text()  # bbox = (x0, top, x1, bottom)
```

### Field Extraction (e.g. invoices)

```python
import re

patterns = {
    "invoice_number": r"Invoice\s*#?\s*(\d+)",
    "date": r"Date:\s*([\d/\-]+)",
    "total": r"Total:\s*\$?([\d,]+\.?\d*)",
}
data = {
    key: (m.group(1) if (m := re.search(p, text, re.IGNORECASE)) else None)
    for key, p in patterns.items()
}
```

## Output Formats

JSON for structured extraction:

```python
output = {
    "metadata": {"title": "...", "pages": 5},
    "pages": [{"page_number": 1, "text": "...", "tables": [...]}],
}
```

CSV for table data: `csv.writer(f).writerows(table)`.

## Workflow

1. Try native PDF reading only when the runtime supports it.
2. Assess structure: tables? forms? pure text?
3. Choose tool: simple text → `pdftotext`; tables → `pdfplumber`; forms → `pypdf`; scanned/image pages → image conversion or OCR-capable reader.
4. Extract and validate the data.
5. Format output (JSON, CSV, or Markdown).

## Failure Handling

- **Encrypted PDF**: check with `pdfinfo`; may need a password — ask the user, do not guess
- **Scanned/image PDF**: use an OCR-capable reader or convert pages to images before extraction; `pdftotext` alone is not enough.
- **Garbled text**: try a different extraction method before reporting
- **Missing tables**: adjust pdfplumber table settings

```python
table_settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
tables = page.extract_tables(table_settings)
```

If content cannot be reliably extracted (scanned images, encryption), report the failure explicitly rather than inventing values. If the task would require changes beyond extraction, stop and ask.
