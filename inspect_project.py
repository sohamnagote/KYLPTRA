with open("backend/main.py", "r", encoding="utf-8") as f:
    text = f.read()

lines = text.splitlines()
for idx, line in enumerate(lines):
    if "/transcript" in line:
        print(f"Line {idx+1}: {line}")
