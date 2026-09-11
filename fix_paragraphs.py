import re

with open('backend/thesis_workspace.php', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: sec.paragraphs || [sec.content || ""] 
# to: (sec.paragraphs && sec.paragraphs.length > 0) ? sec.paragraphs : [sec.content || ""]
old = 'const paragraphs = sec.paragraphs || [sec.content || ""];'
new = 'const paragraphs = (sec.paragraphs && sec.paragraphs.length > 0) ? sec.paragraphs : [sec.content || ""];'

if old in content:
    content = content.replace(old, new)
    with open('backend/thesis_workspace.php', 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIXED: Updated paragraphs fallback logic")
else:
    print("NOT FOUND: Could not find exact string")
    # Try to find it with flexible whitespace
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'sec.paragraphs || [sec.content' in line:
            print(f"  Found at line {i+1}: {repr(line)}")
