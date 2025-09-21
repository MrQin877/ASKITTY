import os
import json
import math
import base64
import boto3

ddb = boto3.client("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name=os.environ["BEDROCK_REGION"])

TABLE       = os.environ["TABLE_NAME"]
EMBED_MODEL = os.environ["EMBED_MODEL_ID"]      # e.g. amazon.titan-embed-text-v2:0
CHAT_MODEL  = os.environ["CHAT_MODEL_ID"]       # e.g. amazon.nova-micro-v1:0

# allow the cors
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "https://d2203w8umw4us0.cloudfront.net")
CORS = {
    "Access-Control-Allow-Origin": FRONTEND_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Access-Control-Max-Age": "3600",
}

# ---------- Helpers ----------
def _resp(status: int, body: dict | str | None = None, extra_headers: dict | None = None):
    payload = body if isinstance(body, str) else json.dumps(body or {})
    headers = {**CORS, "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return {"statusCode": status, "headers": headers, "body": payload}

def _method(event) -> str:
    return (
        (event.get("httpMethod") or "")
        or (event.get("requestContext", {}).get("http", {}).get("method") or "")
    ).upper()

def _parse_body(event) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8", "ignore")
        except Exception:
            raw = "{}"
    try:
        return json.loads(raw)
    except Exception:
        return {}

# ---------- Bedrock ----------
def titan_embed(q: str):
    body = json.dumps({"inputText": q})
    resp = bedrock.invoke_model(
        modelId=EMBED_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(resp["body"].read())["embedding"]

def cosine(a, b):
    s = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)) + 1e-9
    nb = math.sqrt(sum(y*y for y in b)) + 1e-9
    return s / (na * nb)

def ask_llm(question: str, passages: list[dict]):
    if not passages:
        return "I don't know based on the indexed documents."

    ctx = "\n\n".join([f"[{i+1}] {p['text']}" for i, p in enumerate(passages)])
    user_prompt = (
        "You are a helpful assistant for internal document QA. "
        "Answer strictly using the provided context. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{ctx}\n\nQuestion: {question}\nAnswer:"
    )

    body = json.dumps({
        "messages": [
            {"role": "user", "content": [{"text": user_prompt}]}
        ],
        "inferenceConfig": {"maxTokens": 300, "temperature": 0.2, "topP": 0.9},
    })

    resp = bedrock.invoke_model(
        modelId=CHAT_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    out = json.loads(resp["body"].read())
    msg = out.get("output", {}).get("message", {})
    parts = [c.get("text") for c in (msg.get("content", []) or []) if c.get("text")]
    return "".join(parts) if parts else ""

# ---------- Handler ----------
def lambda_handler(event, context):
    "Pre-check: allow directly (be sure to also attach this Lambda to the OPTIONS route)"
    if _method(event) == "OPTIONS":
        return {"statusCode": 204, "headers": CORS, "body": ""}

    try:
        body = _parse_body(event)
        q = (body.get("question") or "").strip()
        if not q:
            return _resp(400, {"error": "missing question"})

        # 1) Embedding
        qvec = titan_embed(q)

        # 2) Scan and check by pk
        items = []
        scan = ddb.scan(TableName=TABLE)
        items.extend(scan.get("Items", []))
        while "LastEvaluatedKey" in scan and len(items) < 5000:
            scan = ddb.scan(TableName=TABLE, ExclusiveStartKey=scan["LastEvaluatedKey"])
            items.extend(scan.get("Items", []))

        # 3) sort
        scored = []
        for it in items:
            try:
                vec = json.loads(it["embedding"]["S"])
                sim = cosine(qvec, vec)
                scored.append((sim, it))
            except Exception:
                continue
        scored.sort(key=lambda x: x[0], reverse=True)
        top_items = [x[1] for x in scored[:8]]

        passages = [{
            "text": it["text"]["S"],
            "fileName": it["s3Key"]["S"].split("/")[-1],
            "s3Key": it["s3Key"]["S"],
            "pageStart": 1,
        } for it in top_items]

        # 4) LLM 生成
        answer = ask_llm(q, passages)

        return _resp(200, {"answer": answer, "references": passages})

    except Exception as e:
        return _resp(500, {"error": str(e)})
