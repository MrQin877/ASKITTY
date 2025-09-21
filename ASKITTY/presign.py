import os
import json
import boto3
import base64

s3 = boto3.client("s3")
BUCKET = os.environ["DOCS_BUCKET"]

# 允许从环境变量覆盖前端域名，便于不同环境
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "https://d2203w8umw4us0.cloudfront.net")

CORS = {
    "Access-Control-Allow-Origin": FRONTEND_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Access-Control-Max-Age": "3600",
}

def _response(status: int, body: dict | str | None = None, extra_headers: dict | None = None):
    payload = body if isinstance(body, str) else json.dumps(body or {})
    headers = {**CORS, "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return {"statusCode": status, "headers": headers, "body": payload}

def _get_method(event) -> str:
    # 支持 REST(REST API) 与 HTTP(API Gateway HTTP API) 两种 event 形态
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

def lambda_handler(event, context):
    method = _get_method(event)

    # 1) 预检请求 —— 直接放行（注意也要把该 Lambda 绑定到 OPTIONS 路由）
    if method == "OPTIONS":
        # 204 更语义化（无响应体）
        return {"statusCode": 204, "headers": CORS, "body": ""}

    # 2) 业务逻辑（POST）
    try:
        body = _parse_body(event)
        key = (body.get("s3Key") or "").strip()

        if not key:
            return _response(400, {"error": "missing s3Key"})

        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=900,  # 15 分钟
        )

        return _response(200, {"url": url})

    except Exception as e:
        # 返回可见错误信息（生产环境可改成通用提示）
        return _response(500, {"error": str(e)})
