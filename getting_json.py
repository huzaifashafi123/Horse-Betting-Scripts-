from groq import Groq
import base64
import os
import json
import time
import glob
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Load .env file
API_KEYS = [
    os.getenv("API_KEY_1"),
    os.getenv("API_KEY_2"),
    os.getenv("API_KEY_3"),
]
    # # Add more API keys as needed
MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct"
]

INPUT_FOLDER = r"cropped_images_1"  # Change this to your input folder path
OUTPUT_FOLDER = "output_json"  # Change this to your output folder path
DELAY_SECONDS = 3  # Delay between requests to avoid rate limiting

def encode_image(image_path):
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def create_prompt():
    """Create a detailed prompt for extracting horse racing data"""
    return """
    Analyze this horse racing image and extract the race results data. 
    
    For each horse in the results, extract the following information and return it as a JSON array:
    - last_raced: Date and track code (e.g., "12Jun25 'BTP'")
    - pgm: Program number
    - horse_name: Name of the horse
    - jockey: Jockey name
    - wgt_me: Weight and equipment info
    - pp: Post position
    - start: Starting position
    - quarter: Quarter mile position
    - half: Half mile position  
    - three_quarter: Three quarter mile position
    - str: Stretch position
    - fin: Final position
    - odds: Betting odds (as number)
    - comments: Race comments
    
    Example format:
    [
        {
            "last_raced": "12Jun25 'BTP'",
            "pgm": 4,
            "horse_name": "Long Shorts",
            "jockey": "Hernandez, Jann",
            "wgt_me": "119 L bf",
            "pp": 4,
            "start": 4,
            "quarter": "4²",
            "half": "4²",
            "three_quarter": "4³",
            "str": "4³ ¹/²",
            "fin": "1¹/²",
            "odds": 2.30,
            "comments": "urged 3/8 all out, up"
        }
    ]
    
    Return ONLY the JSON array, no other text and please dont convert the power into number.
    """

def process_image_with_groq(image_path, api_key, model):
    """Process a single image with Groq API"""
    try:
        # Encode image
        base64_image = encode_image(image_path)
        
        # Create client - this should work after fixing httpx version
        client = Groq(api_key=api_key)
        
        # Create chat completion
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": create_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model=model,
        )
        
        response_content = chat_completion.choices[0].message.content
        
        # Try to parse JSON from response
        try:
            # Clean the response - remove any markdown formatting
            cleaned_response = response_content.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            parsed_data = json.loads(cleaned_response)
            return parsed_data
        except json.JSONDecodeError as e:
            print(f"JSON parsing error for {image_path}: {e}")
            print(f"Raw response: {response_content}")
            return None
            
    except Exception as e:
        print(f"Error processing {image_path} with {model}: {e}")
        return None

def get_image_files(folder_path):
    """Get all image files from the folder with better debugging"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    image_files = []
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist!")
        return []
    
    # Get all files in the folder
    all_files = os.listdir(folder_path)
    print(f"All files in folder: {all_files}")
    
    # Filter for image files (case-insensitive)
    for file in all_files:
        file_path = os.path.join(folder_path, file)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
            
        # Check if file has an image extension (case-insensitive)
        file_lower = file.lower()
        for ext in image_extensions:
            if file_lower.endswith(ext):
                image_files.append(file_path)
                print(f"Found image: {file}")
                break
    
    # Remove duplicates (just in case)
    image_files = list(set(image_files))
    
    return image_files

def debug_folder_contents(folder_path):
    """Debug function to see all folder contents"""
    print(f"\nDebugging folder: {folder_path}")
    print("=" * 50)
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist!")
        return
    
    all_items = os.listdir(folder_path)
    print(f"Total items in folder: {len(all_items)}")
    
    for item in all_items:
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            print(f"  [DIR]  {item}")
        else:
            # Get file size
            size = os.path.getsize(item_path)
            print(f"  [FILE] {item} ({size} bytes)")
    
    print("=" * 50)

def save_json_result(data, output_path):
    """Save the extracted data as JSON"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving {output_path}: {e}")
        return False

def main():
    """Main function to process all images"""
    # Create output folder if it doesn't exist
    Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    
    # DEBUG: Show folder contents
    debug_folder_contents(INPUT_FOLDER)
    
    # Get all image files
    image_files = get_image_files(INPUT_FOLDER)
    
    if not image_files:
        print(f"No image files found in {INPUT_FOLDER}")
        return
    
    print(f"\nFound {len(image_files)} image files to process")
    print("Image files:")
    for i, img in enumerate(image_files, 1):
        print(f"  {i}. {os.path.basename(img)}")
    
    # Ask for confirmation before processing
    user_input = input(f"\nProceed with processing {len(image_files)} images? (y/n): ")
    if user_input.lower() != 'y':
        print("Processing cancelled.")
        return
    
    print("\nStarting processing...")
    print("=" * 50)
    
    # Process each image
    api_key_index = 0
    model_index = 0
    
    for i, image_path in enumerate(image_files):
        print(f"\nProcessing {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
        
        # Get current API key and model
        current_api_key = API_KEYS[api_key_index % len(API_KEYS)]
        current_model = MODELS[model_index % len(MODELS)]
        
        print(f"Using API key {api_key_index + 1} with model: {current_model}")
        
        # Process the image
        result = process_image_with_groq(image_path, current_api_key, current_model)
        
        if result:
            # Create output filename
            image_filename = Path(image_path).stem
            output_filename = f"{image_filename}.json"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            # Save result
            save_json_result(result, output_path)
        else:
            print(f"Failed to process {image_path}")
        
        # Rotate API keys and models
        api_key_index = (api_key_index + 1) % len(API_KEYS)
        model_index = (model_index + 1) % len(MODELS)
        
        # Wait before next request (except for the last image)
        if i < len(image_files) - 1:
            print(f"Waiting {DELAY_SECONDS} seconds before next request...")
            time.sleep(DELAY_SECONDS)
    
    print(f"\nProcessing complete! Results saved in {OUTPUT_FOLDER}")

if __name__ == "__main__":
    # Update these paths and API keys before running
    print("Horse Racing Data Extractor")
    print("=" * 50)
    print(f"Input folder: {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"API keys configured: {len(API_KEYS)}")
    print(f"Models configured: {len(MODELS)}")
    print(f"Delay between requests: {DELAY_SECONDS} seconds")
    print("=" * 50)
    
    main()