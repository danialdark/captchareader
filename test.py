from PIL import Image, ImageFilter, ImageOps
import pytesseract
import os

# --- LOAD IMAGE ---
# Image file named "test.png" in same folder as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "image.png")

if not os.path.exists(image_path):
    print("❌ Image file 'test.png' not found in script folder!")
    exit(1)

img = Image.open(image_path)

# --- PREPROCESS IMAGE ---
img = img.convert("L")                      # convert to grayscale
img = ImageOps.invert(img)                  # invert colors
img = img.point(lambda x: 0 if x < 140 else 255)  # threshold
img = img.filter(ImageFilter.MedianFilter()) # reduce noise

# --- RUN OCR ---
captcha_text = pytesseract.image_to_string(img, config="--psm 8")
captcha_text = captcha_text.strip()

# --- OUTPUT ---
print("✅ Detected CAPTCHA:", captcha_text)
