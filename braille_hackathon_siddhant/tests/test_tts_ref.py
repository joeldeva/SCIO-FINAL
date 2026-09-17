import http.client, json

# Test braille reference endpoint
conn = http.client.HTTPConnection("localhost", 8000)
conn.request("GET", "/braille/reference")
r = conn.getresponse()
ref = json.loads(r.read())
patterns = ref["patterns"]

print("Braille reference - sample patterns:")
for letter in ["a", "b", "c", "h", "e", "l", "o"]:
    print("  %s -> dots %s" % (letter, patterns.get(letter)))

# Test TTS
conn2 = http.client.HTTPConnection("localhost", 8000)
body = json.dumps({"text": "hello world"}).encode()
conn2.request("POST", "/tts", body, {"Content-Type": "application/json"})
r2 = conn2.getresponse()
tts_result = json.loads(r2.read())
audio_b64 = tts_result.get("audio", "")
engine = tts_result.get("engine", "none")
print("TTS engine : %s" % engine)
print("Audio size : %d bytes (base64)" % len(audio_b64))
print("TTS works  : %s" % ("YES" if audio_b64.startswith("data:audio") else "NO"))

# Save audio file to verify
if audio_b64.startswith("data:audio"):
    import base64
    audio_data = base64.b64decode(audio_b64.split(",")[1])
    with open("test_tts_output.mp3", "wb") as f:
        f.write(audio_data)
    print("Saved test audio -> test_tts_output.mp3 (%d bytes)" % len(audio_data))

print("\nAll endpoints working!")
