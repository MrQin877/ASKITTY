import boto3, json, os, re
from botocore.config import Config

BUCKET = os.environ.get("BUCKET_NAME") or os.environ.get("DOCS_BUCKET")
REGION = os.environ.get("BUCKET_REGION") or os.environ.get("AWS_REGION")
ORIGIN = os.environ.get("CORS_ORIGIN", "https://d2203w8umw4us0.cloudfront.net")

s3 = boto3.client("s3", region_name=REGION, config=Config(s3={"addressing_style": "virtual"}))

CORS = {
    "Access-Control-Allow-Origin": ORIGIN,
    "Access-Control-Allow-Methods": "OPTIONS,PUT,POST",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}

def sanitize_key(path: str) -> str:
    # keep subfolders; sanitize each part
    parts = [re.sub(r"[^a-zA-Z0-9._-]", "_", p) for p in path.split("/")]
    return "/".join(p for p in parts if p)

def lambda_handler(event, context):
    try:
        if event.get("httpMethod") == "OPTIONS":
            return {"statusCode": 200, "headers": CORS, "body": ""}

        if not BUCKET:
            return {"statusCode": 500, "headers": CORS, "body": json.dumps({"error":"Bucket env missing"})}

        body = json.loads(event.get("body") or "{}")
        # Prefer explicit objectKey; fallback to filename at root.
        object_key = body.get("objectKey")
        if not object_key:
            filename = body.get("filename")
            if not filename:
                return {"statusCode": 400, "headers": CORS, "body": json.dumps({"error":"objectKey or filename is required"})}
            object_key = f"uploads/{filename}"

        object_key = sanitize_key(object_key)
        params = {"Bucket": BUCKET, "Key": object_key}

        # Sign with ContentType only if provided, and send the same header on PUT
        ct = body.get("contentType")
        if ct:
            params["ContentType"] = ct

        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=900,
            HttpMethod="PUT",
        )

        return {
            "statusCode": 200,
            "headers": CORS,
            "body": json.dumps({"uploadUrl": url, "key": object_key, "bucket": BUCKET})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {**CORS, "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }
