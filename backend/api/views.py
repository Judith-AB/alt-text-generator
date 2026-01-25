from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image

# Initialize model and processor at module level for persistence
processor = BlipProcessor.from_pretrained(
    "Salesforce/blip-image-captioning-base",
     use_fast=True
)
model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base"
)

def clean_for_accessibility(text):
    """
    Final polish to ensure the description is direct and compliant with WCAG.
    Removes redundant AI-isms and instructional phrases.
    """
    to_strip = [
        "is a description of", "is the purpose of", "this image shows",
        "description:", "alt-text:", "purpose:", "the image contains"
    ]
    
    # Standard WCAG redundancy removal
    redundant = ["an image of", "a photo of", "a picture of", "graphic of", "photograph of"]
    
    cleaned = text.lower()
    
    # Remove instructional artifacts
    for phrase in to_strip:
        cleaned = cleaned.replace(phrase, "")
        
    # Remove redundant "image of" labels
    for phrase in redundant:
        cleaned = cleaned.replace(phrase, "")

    return " ".join(cleaned.split()).capitalize()

@api_view(['POST'])
def generate_alt_text(request):
    image_file = request.FILES.get('image')
    # Default to 'simple' if no mode is provided by the frontend
    mode = request.data.get('mode', 'simple')

    if not image_file:
        return Response({"error": "No image provided"}, status=400)

    try:
        image = Image.open(image_file).convert("RGB")
    except Exception as e:
        return Response({"error": f"Invalid image file: {str(e)}"}, status=400)

    # 1. Enhanced Instruction-Based Prompts
    # Using descriptive instructions helps the model understand its role without 
    # necessarily repeating the prompt in the output.
   
    # Hybrid prompts: short triggers that BLIP understands better
    prompt_map = {
    "simple": "A photo of", 
    "detailed": "A detailed description of",
    "functional": "This icon represents"
}
    
    prompt = prompt_map.get(mode, prompt_map["simple"])

    # 2. Complexity-Specific Generation Parameters
    gen_configs = {
        "simple": {"max_new_tokens": 30, "min_new_tokens": 5},
        "detailed": {"max_new_tokens": 80, "min_new_tokens": 30, "repetition_penalty": 1.2},
        "functional": {"max_new_tokens": 40, "min_new_tokens": 10}
    }
    config = gen_configs.get(mode, gen_configs["simple"])

    # Prepare inputs with the specific instruction
    inputs = processor(image, text=prompt, return_tensors="pt")
    
    # Generate output
    output = model.generate(**inputs, **config)
    
    # Decode the result
    raw_caption = processor.decode(output[0], skip_special_tokens=True)
    
    # 3. Strict Stripping Logic
    # If the model echoes the prompt instruction, remove it so the user 
    # only hears the actual description.
    if raw_caption.lower().startswith(prompt.lower()):
        raw_caption = raw_caption[len(prompt):].strip()
    elif ":" in raw_caption[:len(prompt)+5]:
        # Handle cases where the model might slightly vary the prompt format
        raw_caption = raw_caption.split(":", 1)[-1].strip()

    # 4. WCAG-Aligned Post-Processing
    final_caption = clean_for_accessibility(raw_caption)

    return Response({
        "alt_text": final_caption,
        "mode_applied": mode
    })