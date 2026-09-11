import urllib.request
import re
import struct
import sys
import os
from PIL import Image

def render_dragon_eye(target_normal_path, target_bad_path):
    url = "https://raw.githubusercontent.com/upiir/dual_lcd_robot_eyes/main/ARDUINO_robot_eyes_dualeye_waveshare_display/data/dragonEye.h"
    print(f"Downloading {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading dragonEye.h: {e}")
        return False
        
    def extract_array(name):
        print(f"Extracting array '{name}'...")
        match = re.search(rf'const\s+uint16_t\s+{name}\[.*?\]\s*(?:PROGMEM\s*)?=\s*\{{(.*?)\}};', content, re.DOTALL)
        if not match:
            # Try without const or PROGMEM
            match = re.search(rf'uint16_t\s+{name}\[.*?\]\s*=\s*\{{(.*?)\}};', content, re.DOTALL)
        if not match:
            print(f"Failed to find array '{name}'")
            return None
        hex_values = re.findall(r'0[xX][0-9a-fA-F]+', match.group(1))
        return [int(val, 16) for val in hex_values]
        
    sclera = extract_array("sclera")
    iris = extract_array("iris")
    polar = extract_array("polar")
    
    if not sclera or not iris or not polar:
        print("Error: Missing one or more required arrays!")
        return False
        
    print(f"Loaded arrays. Sclera: {len(sclera)}, Iris: {len(iris)}, Polar: {len(polar)}")
    
    # Render the eye
    width = 160
    height = 160
    
    rendered_pixels = []
    for y in range(height):
        for x in range(width):
            idx = y * width + x
            p = polar[idx]
            d = p & 0x7F
            a = p >> 7
            
            if d < 80:
                # Inside the iris area
                color = iris[d * 512 + a]
            else:
                # Outside (sclera background)
                color = sclera[idx]
                
            # The color is in RGB565. Let's convert it to standard RGB (8-bit) for debugging / PNG saving
            r = ((color >> 11) & 0x1F) << 3
            g = ((color >> 5) & 0x3F) << 2
            b = (color & 0x1F) << 3
            rendered_pixels.append((r, g, b))
            
    # Save as PNG
    img = Image.new("RGB", (width, height))
    img.putdata(rendered_pixels)
    png_path = os.path.join(os.path.dirname(target_normal_path), "dragon_rendered.png")
    img.save(png_path)
    print(f"Saved flat reconstructed PNG to {png_path}!")
    
    # Save as RGB565 binary format (matching what our firmware expects: each pixel written as 16-bit little-endian)
    def save_bin(target_path):
        with open(target_path, "wb") as f:
            for y in range(height):
                for x in range(width):
                    idx = y * width + x
                    p = polar[idx]
                    d = p & 0x7F
                    a = p >> 7
                    
                    if d < 80:
                        color = iris[d * 512 + a]
                    else:
                        color = sclera[idx]
                    
                    # Write as 16-bit little-endian
                    f.write(struct.pack("<H", color))
        print(f"Saved binary file to {target_path}!")
        
    save_bin(target_normal_path)
    save_bin(target_bad_path)
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python render_eye.py <target_normal_bin_path> <target_bad_bin_path>")
        sys.exit(1)
    render_dragon_eye(sys.argv[1], sys.argv[2])
