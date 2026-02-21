import os
import random
import sys
from PIL import Image

# Force Reload
for name in list(sys.modules.keys()):
    if name not in ("sys", "os", "random", "PIL.Image"):
        del sys.modules[name]

# Verify Image Validity
def isImageValid(path):
    try:
        imageFile = Image.open(path)
        imageFile.save(path)
        return True
    
    except:
        return False

# Paths
originalPath = "C:/Users/Admin/Documents/Compositing/CorsicanLandscape_SourceWater.jpg"
numberOfGlitches = 1
numberOfImages = 10

# Read Original
with open(originalPath, "rb") as f:
    originalContent = f.read()

# Split the original filename into base and extension (for saving new files)
base, ext = os.path.splitext(originalPath)

# Loop
for frame in range(numberOfImages):
    
    valid = False
    attempt = 0
    
    while not valid:
        attempt += 1
        # Copy Originale Content
        data = bytearray(originalContent)
        
        # Alter Random Bytes
        start_idx = 200 if len(data) > 200 else 0
        
        for i in range(numberOfGlitches):
            idx = random.randint(start_idx, len(data)-1)
            data[idx] = random.randint(0, 255)

        # Create Path
        out_path = f"{base}_GLITCH_{str(frame).zfill(3)}{ext}"

        # Save Glitch
        with open(out_path, "wb") as out_f:
            out_f.write(data)
            
        # Check Validity
        valid = isImageValid(out_path)
        if not valid:
            print(f"Invalid image, retrying... (attempt {attempt})")

    print("Created :", out_path)

print("Done.")