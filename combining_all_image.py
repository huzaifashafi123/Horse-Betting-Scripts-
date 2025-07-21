import os
import shutil

# Set your main directory containing subfolders
source_dir = r'cropped_images'  # <-- Replace this
destination_dir = r'cropped_image'  # <-- Replace this

# Create destination folder if it doesn't exist
os.makedirs(destination_dir, exist_ok=True)

# Supported image extensions
image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')

# Loop through all folders and subfolders
for root, dirs, files in os.walk(source_dir):
    for file in files:
        if file.lower().endswith(image_extensions):
            src_path = os.path.join(root, file)
            dst_path = os.path.join(destination_dir, file)

            # Avoid overwriting by renaming if duplicate filename
            base, ext = os.path.splitext(file)
            counter = 1
            while os.path.exists(dst_path):
                dst_path = os.path.join(destination_dir, f"{base}_{counter}{ext}")
                counter += 1

            shutil.move(src_path, dst_path)

print("✅ All images moved to single folder.")
