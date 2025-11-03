#!/usr/bin/env python3
"""
CAPTCHA reader that:
1) Tries multiple local preprocessing strategies with pytesseract.
2) If local OCR confidence is low or result empty, falls back to 2Captcha service.

Place this script in the same folder as test.png and run:
    python3 test.py

If you want to use 2Captcha fallback, set API_KEY_2CAPTCHA to your API key.
"""

import os
import time
import requests
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import pytesseract
import sys

# ---------- CONFIG ----------
IMAGE_NAME = "image.png"               # image file near the script
MIN_ACCEPT_CONFIDENCE = 45           # accept if mean OCR confidence >= this
USE_2CAPTCHA_FALLBACK = True         # set False to disable remote solver
API_KEY_2CAPTCHA = "YOUR_2CAPTCHA_API_KEY"  # <-- replace if using 2Captcha
TESSERACT_CMD = None                  # e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# ----------------------------

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, IMAGE_NAME)

if not os.path.exists(image_path):
    print(f"❌ Image file '{IMAGE_NAME}' not found in script folder: {script_dir}")
    sys.exit(1)

def ocr_with_config(img, psm=8, oem=3, whitelist=None):
    cfg = f"--psm {psm} --oem {oem}"
    if whitelist:
        cfg += f" -c tessedit_char_whitelist={whitelist}"
    # Return full data so we can compute confidence
    data = pytesseract.image_to_data(img, config=cfg, output_type=pytesseract.Output.DICT)
    # Combine text
    text = " ".join([w for w in data.get('text', []) if w.strip()])
    # Extract numerical confidences (skip -1)
    confs = [int(c) for c in data.get('conf', []) if c and c != '-1']
    mean_conf = int(sum(confs) / len(confs)) if confs else 0
    return text.strip(), mean_conf, data

def preprocess_variants(image):
    """
    Yield several preprocessed PIL Image variants to try.
    """
    # base grayscale
    gray = image.convert("L")

    # 1) simple threshold (good for light background dark text)
    yield gray.point(lambda x: 0 if x < 140 else 255)

    # 2) inverted + threshold (good for dark background light text)
    inv = ImageOps.invert(gray)
    yield inv.point(lambda x: 0 if x < 140 else 255)

    # 3) enhanced contrast + sharpen
    enh = ImageEnhance.Contrast(gray).enhance(2.0)
    enh = enh.filter(ImageFilter.MedianFilter(size=3))
    yield enh.point(lambda x: 0 if x < 150 else 255)

    # 4) resize + blur removal
    w, h = gray.size
    scale = 2
    big = gray.resize((w*scale, h*scale))
    big = big.filter(ImageFilter.MedianFilter(size=3))
    yield big.point(lambda x: 0 if x < 140 else 255)

    # 5) morphological-ish approach: opening-like by repeated filters
    img2 = gray.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    yield img2.point(lambda x: 0 if x < 140 else 255)

def try_local_ocr(image_path):
    img_orig = Image.open(image_path)
    best_text = ""
    best_conf = -1
    best_variant_index = -1

    for i, variant in enumerate(preprocess_variants(img_orig)):
        # try a couple of psm / whitelist combos that commonly help CAPTCHAs
        attempts = [
            {"psm": 8, "whitelist": None},      # single word
            {"psm": 7, "whitelist": None},      # single text line
            {"psm": 8, "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"},
            {"psm": 7, "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"}  # uppercase/digits
        ]
        for a in attempts:
            text, conf, _ = ocr_with_config(variant, psm=a["psm"], whitelist=a["whitelist"])
            text = text.replace(" ", "")  # remove spaces — CAPTCHAs often are contiguous
            # Debug print each try (comment out if noisy)
            # print(f"[variant {i} psm{a['psm']}] -> '{text}' conf={conf}")
            if text and conf > best_conf:
                best_text, best_conf = text, conf
                best_variant_index = i
            # Early accept
            if text and conf >= MIN_ACCEPT_CONFIDENCE:
                return text, conf, i
    return best_text, best_conf, best_variant_index

# -------------- 2Captcha integration --------------
def solve_with_2captcha(image_path, api_key, wait_seconds=5, max_wait=120):
    """
    Sends image to 2captcha, polls for result.
    Returns solved text or empty string on failure.
    """
    if not api_key or api_key == "YOUR_2CAPTCHA_API_KEY":
        print("⚠️ 2Captcha API key not set. Skipping remote fallback.")
        return ""
    print("→ Uploading to 2Captcha...")
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {'key': api_key, 'method': 'post'}
        r = requests.post("http://2captcha.com/in.php", files=files, data=data)
    if r.status_code != 200:
        print("2Captcha upload failed:", r.text)
        return ""
    resp = r.text
    if not resp.startswith("OK|"):
        print("2Captcha error:", resp)
        return ""
    captcha_id = resp.split("|")[1]
    print(f"→ Sent, captcha id = {captcha_id}. Polling for result...")
    fetch_url = "http://2captcha.com/res.php"
    waited = 0
    while waited < max_wait:
        time.sleep(wait_seconds)
        waited += wait_seconds
        params = {'key': api_key, 'action': 'get', 'id': captcha_id}
        r2 = requests.get(fetch_url, params=params)
        if r2.status_code != 200:
            continue
        txt = r2.text
        if txt == "CAPCHA_NOT_READY":
            # still processing
            continue
        if txt.startswith("OK|"):
            solution = txt.split("|", 1)[1]
            return solution.strip()
        else:
            print("2Captcha error while polling:", txt)
            return ""
    print("2Captcha timed out.")
    return ""

# ---------------- main flow ----------------
print("Starting local OCR attempts...")
local_text, local_conf, variant_idx = try_local_ocr(image_path)
if local_text:
    print(f"Local OCR best: '{local_text}' (confidence={local_conf}, variant={variant_idx})")
else:
    print("Local OCR produced no text or very low confidence.")

if local_text and local_conf >= MIN_ACCEPT_CONFIDENCE:
    print("✅ Accepted local OCR result:", local_text)
    sys.exit(0)

if USE_2CAPTCHA_FALLBACK:
    print("Falling back to 2Captcha solver...")
    remote_solution = solve_with_2captcha(image_path, API_KEY_2CAPTCHA)
    if remote_solution:
        print("✅ 2Captcha solution:", remote_solution)
        sys.exit(0)
    else:
        print("❌ 2Captcha failed or not configured.")
# final fallback print whatever local returned
print("Final result (best local attempt):", local_text, f"(confidence={local_conf})")
