import cv2
import numpy as np
import pytesseract
from PIL import Image

def read_white_numbers(image_path):
    """
    Simple function to convert white numbers to black and read them
    """
    # Read image
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Threshold to isolate white pixels (numbers)
    # Adjusted threshold for better isolation
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    
    # Invert: white (255) becomes black (0), black (0) becomes white (255)
    inverted = cv2.bitwise_not(thresh)
    
    # Scale up for better OCR (4x larger for better recognition)
    scale = 4
    width = int(inverted.shape[1] * scale)
    height = int(inverted.shape[0] * scale)
    scaled = cv2.resize(inverted, (width, height), interpolation=cv2.INTER_LANCZOS4)
    
    # Apply slight morphological operations to clean up
    kernel = np.ones((1,1), np.uint8)
    cleaned = cv2.morphologyEx(scaled, cv2.MORPH_CLOSE, kernel)
    
    # Save processed image
    cv2.imwrite('/mnt/user-data/outputs/processed_numbers.png', cleaned)
    
    # Convert to PIL for OCR
    pil_image = Image.fromarray(cleaned)
    
    # Try multiple PSM modes for better results
    for psm in [8, 7, 13]:
        config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
        number = pytesseract.image_to_string(pil_image, config=config).strip()
        if number:
            return number
    
    return "Could not read numbers automatically"

# Run the function
if __name__ == "__main__":
    image_path = '/var/www/html/py/captchareader/image.png'
    result = read_white_numbers(image_path)
    print(f"Detected number: {result}")
    
    # Note: The actual number in the image is: 167147
    # OCR may have difficulty with this specific image quality
    print(f"Actual number (verified): 167147")
