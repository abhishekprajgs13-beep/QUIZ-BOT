import fitz

def extract_pages(pdf_bytes: bytes) -> list:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for p in range(len(doc)):
        page = doc[p]
        rect = page.rect
        width = rect.width
        height = rect.height
        items = []
        
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" not in b: 
                continue
            for l in b["lines"]:
                for s in l["spans"]:
                    text = s["text"]
                    if not text.strip(): 
                        continue
                    bbox = s["bbox"] 
                    items.append({
                        "text": text,
                        "x": round(bbox[0]),
                        "y": round(bbox[1]),
                        "w": round(bbox[2] - bbox[0]),
                        "h": round(bbox[3] - bbox[1])
                    })
        pages.append({"items": items, "width": width, "height": height, "pageNum": p + 1})
    return pages
