from PIL import Image
import struct
import sys
import os

def convert(img_path, target_path, width=200, height=200):
    print(f"Loading image {img_path}...")
    try:
        img = Image.open(img_path).convert("RGB")
    except Exception as e:
        print(f"Error loading image: {e}")
        return False
        
    print(f"Resizing to {width}x{height}...")
    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
    pixels = list(img_resized.getdata())
    
    print("Converting pixels to RGB565...")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "wb") as f:
        for r, g, b in pixels:
            # RGB565 format: 5 bits Red, 6 bits Green, 5 bits Blue
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            # Write as 16-bit little endian
            f.write(struct.pack("<H", rgb565))
            
    print(f"Saved binary file to {target_path}!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_image.py <source_img_path> <target_bin_path> [width] [height]")
        sys.exit(1)
        
    src = sys.argv[1]
    dst = sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    convert(src, dst, w, h)
