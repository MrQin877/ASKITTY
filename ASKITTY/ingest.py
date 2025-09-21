import os, io, re, json
import boto3
from typing import Optional, List, Tuple

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name=os.environ["BEDROCK_REGION"])

BUCKET = os.environ["DOCS_BUCKET"]
TABLE  = os.environ["TABLE_NAME"]
EMBED_MODEL = os.environ["EMBED_MODEL_ID"]

# ---------- utilities ----------
def clean_text(t: str) -> str:
    t = re.sub(r"\r\n?", "\n", t)
    t = re.sub(r"[ \t\f\v]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def titan_embed(text: str):
    body = json.dumps({"inputText": text})
    resp = bedrock.invoke_model(modelId=EMBED_MODEL, body=body)
    return json.loads(resp["body"].read())["embedding"]

# Chunker that also emits the pageStart for each chunk
def chunk_with_pages(full_text: str, page_spans: List[Tuple[int,int]], max_chars=3500, overlap=200):
    """
    page_spans = list of (start_index_in_full_text, page_number) sorted by start_index.
    Yields: (chunk_text, pageStart)
    """
    out = []
    i, n = 0, len(full_text)
    step = max_chars - overlap
    def page_for_index(idx: int) -> int:
        # binary search not needed; linear is fine for doc-scale
        current = 1
        for start, pg in page_spans:
            if idx >= start:
                current = pg
            else:
                break
        return current

    while i < n:
        j = min(i + max_chars, n)
        ck = full_text[i:j]
        pageStart = page_for_index(i)
        out.append((ck, pageStart))
        i += step
    return out

# ---------- extractors ----------
def extract_pdf_pages(byts: bytes) -> Tuple[str, List[Tuple[int,int]]]:
    """
    Returns (full_text, page_spans) where page_spans = [(start_index, page_number), ...]
    """
    # Use pypdf for clean page boundaries
    from pypdf import PdfReader
    rd = PdfReader(io.BytesIO(byts))
    parts = []
    page_spans = []
    current_index = 0
    for i, pg in enumerate(rd.pages, start=1):
        try:
            txt = pg.extract_text() or ""
        except Exception:
            txt = ""
        txt = clean_text(txt)
        page_spans.append((current_index, i))
        if txt:
            parts.append(txt)
            current_index += len(txt) + 1  # +1 for the newline we’ll add
        else:
            # keep an empty marker so indices still advance predictably
            parts.append("")
            current_index += 1
    full = "\n".join(parts)
    return full, page_spans

def extract_pdf_flat(byts: bytes) -> str:
    # Fallback single-string extractor (no page info)
    from pdfminer.high_level import extract_text
    return clean_text(extract_text(io.BytesIO(byts)) or "")

def extract_docx(byts: bytes) -> str:
    import mammoth
    result = mammoth.extract_raw_text(io.BytesIO(byts))
    return clean_text(result.value or "")

def extract_txt(byts: bytes) -> str:
    return clean_text(byts.decode("utf-8", errors="ignore"))

# ---------- router ----------
def route_by_extension(ext: str, byts: bytes):
    """
    Returns a tuple: (full_text, page_spans)
      - For PDFs: page_spans has real page mapping.
      - For DOCX/TXT: page_spans = [(0,1)] so pageStart=1.
    """
    ext = (ext or "").lower()
    if ext == ".pdf":
        try:
            full, spans = extract_pdf_pages(byts)
            if full.strip():
                return full, spans
        except Exception:
            pass
        # fallback: flat text only
        flat = extract_pdf_flat(byts)
        return flat, [(0, 1)]
    if ext == ".docx":
        t = extract_docx(byts)
        return t, [(0, 1)]
    if ext in (".txt", ".md", ".log"):
        t = extract_txt(byts)
        return t, [(0, 1)]
    return "", [(0, 1)]   # unsupported

# ---------- handler ----------
def lambda_handler(event, context):
    ddb = boto3.client("dynamodb")

    for rec in event["Records"]:
        key = rec["s3"]["object"]["key"]
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        byts = obj["Body"].read()
        ext = os.path.splitext(key)[1]

        full_text, page_spans = route_by_extension(ext, byts)
        if not full_text.strip():
            continue

        doc_id = key.replace("/", "_")

        # chunk while tracking which page each chunk starts on
        for i, (ck, pageStart) in enumerate(chunk_with_pages(full_text, page_spans)):
            vec = titan_embed(ck)
            item = {
                "pk":        {"S": f"DOC#{doc_id}"},
                "sk":        {"S": f"CHUNK#{i:05d}"},
                "docId":     {"S": doc_id},
                "text":      {"S": ck[:3500]},
                "embedding": {"S": json.dumps(vec)},
                "s3Key":     {"S": key},
                "ext":       {"S": ext or ""},
                "pageStart": {"N": str(pageStart)}
            }
            ddb.put_item(TableName=TABLE, Item=item)

    return {"ok": True}
