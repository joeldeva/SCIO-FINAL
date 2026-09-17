import http.client, json

img_path = "dataset/sample_inputs/hello_clean.jpg"
with open(img_path, "rb") as f:
    img_data = f.read()

boundary = "braillevisionboundary"
body = (
    ("--" + boundary + "\r\n").encode() +
    b'Content-Disposition: form-data; name="file"; filename="hello_clean.jpg"\r\n' +
    b"Content-Type: image/jpeg\r\n\r\n" +
    img_data +
    ("\r\n--" + boundary + "--\r\n").encode()
)

conn = http.client.HTTPConnection("localhost", 8000)
conn.request(
    "POST", "/detect", body,
    {"Content-Type": "multipart/form-data; boundary=" + boundary}
)
r = conn.getresponse()
result = json.loads(r.read())

print("=" * 40)
print("  BrailleVision API Test")
print("=" * 40)
print("Detected text :", result.get("text") or "(none)")
print("Confidence    :", result.get("confidence"))
print("Method        :", result.get("method"))
print("Cells found   :", result.get("cells_detected"))
print("Dots detected :", result.get("dots_detected"))
print("=" * 40)
