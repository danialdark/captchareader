from PIL import Image, ImageFilter, ImageOps
import pytesseract
import os

# --- SETUP TESSERACT PATH ---
# If you installed Tesseract in the default location, keep this:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- LOAD IMAGE ---
# Image file is named "test.png" and located near this Python script
script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "image.png")

# Check if image exists
if not os.path.exists(image_path):
    print("❌ Image file 'test.png' not found in script folder!")
    exit(1)

img = Image.open(image_path)

# --- PREPROCESS IMAGE ---
# Convert to grayscale
img = img.convert("L")

# Invert colors (useful if background is dark)
img = ImageOps.invert(img)

# Apply thresholding to make text more distinct
img = img.point(lambda x: 0 if x < 140 else 255)

# Remove noise using median filter
img = img.filter(ImageFilter.MedianFilter())

# --- RUN OCR ---
# --psm 8 works well for single words/short text CAPTCHAs
captcha_text = pytesseract.image_to_string(img, config="--psm 8")
captcha_text = captcha_text.strip()

# --- OUTPUT ---
print("✅ Detected CAPTCHA:", captcha_text)
