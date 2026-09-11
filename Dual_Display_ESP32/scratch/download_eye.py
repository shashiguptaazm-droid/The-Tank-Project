import urllib.request
import re
import struct
import sys
import os

def download_and_convert(eye_name, target_path):
    url = f"https://raw.githubusercontent.com/upiir/dual_lcd_robot_eyes/main/ARDUINO_robot_eyes_dualeye_waveshare_display/data/{eye_name}.h"
    print(f"Downloading {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading {eye_name}: {e}")
        return False
        
    print("Parsing C array...")
    # Find all hex values like 0x1234 or 0X1234
    hex_values = re.findall(r'0[xX][0-9a-fA-F]+', content)
    if not hex_values:
        print("No hex values found in file!")
        return False
        
    print(f"Found {len(hex_values)} pixels. Converting to binary...")
    
    # Write to bin file
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "wb") as f:
        for val in hex_values:
            pixel = int(val, 16)
            # Write as 16-bit little-endian (or big-endian depending on need)
            # The original code swap_color_bytes swaps the bytes anyway, so let's match the original formatting
            f.write(struct.pack("<H", pixel))
            
    print(f"Saved binary file to {target_path}!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python download_eye.py <eye_name> <target_bin_path>")
        sys.exit(1)
    eye_name = sys.argv[1]
    target_path = sys.argv[2]
    download_and_convert(eye_name, target_path)
