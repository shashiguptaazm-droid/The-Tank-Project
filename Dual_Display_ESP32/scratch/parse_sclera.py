import urllib.request
import re
import struct
import sys
import os

def parse_sclera_array(eye_name, target_path):
    url = f"https://raw.githubusercontent.com/upiir/dual_lcd_robot_eyes/main/ARDUINO_robot_eyes_dualeye_waveshare_display/data/{eye_name}.h"
    print(f"Downloading {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading {eye_name}: {e}")
        return False
        
    print("Finding sclera array block...")
    # Find block: const uint16_t sclera[...] = { ... };
    match = re.search(r'const\s+uint16_t\s+sclera\[.*?\]\s*PROGMEM\s*=\s*\{(.*?)\};', content, re.DOTALL)
    if not match:
        # Try fallback without PROGMEM
        match = re.search(r'const\s+uint16_t\s+sclera\[.*?\]\s*=\s*\{(.*?)\};', content, re.DOTALL)
        
    if not match:
        print("Could not find sclera array block!")
        return False
        
    array_content = match.group(1)
    
    print("Parsing hex values from array...")
    hex_values = re.findall(r'0[xX][0-9a-fA-F]+', array_content)
    if not hex_values:
        print("No hex values found in sclera array!")
        return False
        
    print(f"Parsed {len(hex_values)} pixels. Writing to binary...")
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "wb") as f:
        for val in hex_values:
            pixel = int(val, 16)
            # Write as 16-bit little-endian
            f.write(struct.pack("<H", pixel))
            
    print(f"Saved binary file to {target_path}!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parse_sclera.py <eye_name> <target_bin_path>")
        sys.exit(1)
    eye_name = sys.argv[1]
    target_path = sys.argv[2]
    parse_sclera_array(eye_name, target_path)
