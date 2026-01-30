from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch
import re

# UPGRADE: Switching to the 'large' model for significantly better reasoning
MODEL_ID = "Salesforce/blip-image-captioning-large"

processor = BlipProcessor.from_pretrained(MODEL_ID)
model = BlipForConditionalGeneration.from_pretrained(MODEL_ID)

# Move to GPU if available for faster performance
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def clean_for_accessibility(text, mode="simple"):
    """
    Ensures descriptions follow WCAG 2.1 but KEEPS natural human language.
    
    The goal: Remove AI garbage, keep human-readable descriptions.
    WCAG wants clear communication - not robotic text!
    """
    
    # Remove AI-generated preambles and redundant phrases
    redundant = [
        "is a description of", "is the purpose of", "this image shows",
        "the image depicts", "the picture shows", "this is an image of",
        "description:", "alt-text:", "alt text:", "purpose:", 
        "the image contains", "an image of", "a photo of", "a picture of", 
        "graphic of", "photograph of", "there is a", "there are",
        "showing", "depicting", "illustrating", "displays",
        "this shows", "we can see", "you can see", "it shows",
        "the image is", "this is a"
    ]
    
    cleaned = text.strip()
    
    # Remove redundant phrases but keep natural articles (a, an, the) when they make sense
    for phrase in redundant:
        # Case-insensitive replacement at start of string
        if cleaned.lower().startswith(phrase):
            cleaned = cleaned[len(phrase):].strip()
        # Also check middle of string
        cleaned = re.sub(r'\s+' + re.escape(phrase) + r'\s+', ' ', cleaned, flags=re.IGNORECASE)
    
    # Remove subjective adjectives (WCAG requires objectivity, but keep descriptive ones)
    subjective = [
        "beautiful", "ugly", "nice", "wonderful", "amazing", "stunning",
        "gorgeous", "lovely", "magnificent", "spectacular", "incredible", "awesome"
    ]
    for word in subjective:
        cleaned = re.sub(r'\b' + re.escape(word) + r'\s*', '', cleaned, flags=re.IGNORECASE)
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'\s+([.,!?;:])', r'\1', cleaned)
    cleaned = cleaned.strip(' .,;:')
    
    # Capitalize first letter properly
    if cleaned:
        # Handle "a dog" vs "A dog" naturally
        cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
    
    # For simple mode: keep it concise but natural
    # Don't truncate mid-thought - that's worse than being slightly long
    if mode == "simple" and len(cleaned) > 150:
        # Find last sentence end before 150 chars
        truncate_at = 147
        for punct in ['. ', '! ', '? ']:
            last_punct = cleaned[:truncate_at].rfind(punct)
            if last_punct > 80:  # Only truncate if we have substantial content
                cleaned = cleaned[:last_punct + 1]
                break
    
    return cleaned if cleaned else "Image content unavailable"

def validate_alt_text_wcag(text, image_context=""):
    """
    Validates alt text against WCAG 2.1 Level AA criteria.
    Returns a tuple: (is_valid, suggestions)
    """
    suggestions = []
    
    # Check 1: Length (should be meaningful but concise)
    if len(text) < 5:
        suggestions.append("Alt text is too short. Provide more descriptive content.")
    elif len(text) > 250:
        suggestions.append("Alt text is too long. Consider using a long description instead.")
    
    # Check 2: Redundant phrases
    redundant_patterns = [
        r'\bimage of\b', r'\bpicture of\b', r'\bphoto of\b',
        r'\bgraphic of\b', r'\bscreenshot of\b'
    ]
    for pattern in redundant_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            suggestions.append(f"Remove redundant phrase: '{pattern}' (screen readers already announce 'image')")
    
    # Check 3: Ends with punctuation
    if text and text[-1] not in '.!?':
        suggestions.append("Consider ending with punctuation for better screen reader pause.")
    
    # Check 4: Avoid placeholder text
    placeholders = ['image', 'photo', 'picture', 'graphic', 'untitled', 'img']
    if text.lower().strip() in placeholders:
        suggestions.append("Placeholder text detected. Provide meaningful description.")
    
    is_valid = len(suggestions) == 0
    return is_valid, suggestions

@api_view(['POST'])
def generate_alt_text(request):
    """
    Generate WCAG 2.1 compliant alt text for images.
    
    Modes:
    - simple: Concise description (default, <125 chars recommended)
    - detailed: Comprehensive description for complex images
    - functional: Describes purpose/action (for UI elements, buttons, links)
    - decorative: Returns empty string (for decorative images per WCAG)
    """
    image_file = request.FILES.get('image')
    mode = request.data.get('mode', 'simple')
    context = request.data.get('context', '') 

    if not image_file:
        return Response({"error": "No image provided"}, status=400)


    if mode == "decorative":
        return Response({
            "alt_text": "",
            "mode_applied": "decorative",
            "wcag_note": "Decorative images should have empty alt text (alt='') per WCAG 2.1",
            "is_valid": True
        })

    try:
        image = Image.open(image_file).convert("RGB")
    except Exception as e:
        return Response({"error": f"Invalid image file: {str(e)}"}, status=400)

   
    import numpy as np
    img_array = np.array(image)
    height, width = img_array.shape[:2]
    
 
    center_region = img_array[int(height*0.2):int(height*0.7), int(width*0.2):int(width*0.8)]
    
    if len(center_region.shape) == 3:
        gray_center = np.mean(center_region, axis=2)
    else:
        gray_center = center_region
    
    variance = np.var(gray_center)
    has_text_pattern = variance > 1000  # High variance suggests text/code on screen
    
    # Generate base caption
    inputs = processor(image, return_tensors="pt").to(device)
    config = {
        "max_new_tokens": 40,
        "num_beams": 8,
        "early_stopping": True,
        "repetition_penalty": 1.3,
        "length_penalty": 0.9,
        "no_repeat_ngram_size": 3,
        "num_return_sequences": 1
    }
    
    with torch.no_grad():
        output = model.generate(**inputs, **config)
    
    base_caption = processor.decode(output[0], skip_special_tokens=True)
    base_caption = clean_for_accessibility(base_caption, "simple")
    
    # Enhance based on image analysis
    lower_caption = base_caption.lower()
    is_computer = "laptop" in lower_caption or "computer" in lower_caption
    
    # Now adapt based on mode
    if mode == "simple":
        final_caption = base_caption
    
    elif mode == "detailed":
        # Build detailed caption by adding observed details
        detailed_parts = [base_caption]
        
        if is_computer:
            # Add screen details if we detected text patterns
            if has_text_pattern:
                detailed_parts.append("with content displayed on the screen")
            else:
                detailed_parts.append("with screen visible")
            
            # Add workspace context
            if "desk" in lower_caption or "table" in lower_caption:
                detailed_parts.append("in a workspace setting")
        
        final_caption = ", ".join(detailed_parts)
  
        if len(final_caption) <= len(base_caption) + 5:
           
            detail_config = {
                "max_new_tokens": 50,
                "num_beams": 6,
                "repetition_penalty": 1.4,
                "early_stopping": True,
                "no_repeat_ngram_size": 3,
            }
            
            with torch.no_grad():
                detail_output = model.generate(**inputs, **detail_config)
            
            alt_caption = processor.decode(detail_output[0], skip_special_tokens=True)
            alt_caption = clean_for_accessibility(alt_caption, "detailed")
            
            # Use it if it's longer and doesn't have obvious errors
            if (len(alt_caption) > len(base_caption) + 10 and 
                "as well as well" not in alt_caption.lower() and
                "ub front" not in alt_caption.lower()):
                final_caption = alt_caption
    
    elif mode == "functional":
        if is_computer:
            if has_text_pattern:
            
                final_caption = "Computer with active content displayed, used for work or programming tasks"
            else:
           
                final_caption = "Computer for general computing, work, and digital tasks"
        
        elif "button" in lower_caption:
            final_caption = "Interactive button"
        
        elif "link" in lower_caption or "hyperlink" in lower_caption:
            final_caption = "Clickable link"
        
        elif "form" in lower_caption or "input" in lower_caption or "field" in lower_caption:
            final_caption = "Input field for entering information"
        
        elif "menu" in lower_caption or "navigation" in lower_caption:
            final_caption = "Navigation element"
        
        elif "icon" in lower_caption:
            final_caption = "Interactive icon"
        
        else:
            final_caption = "Interactive element"
    
    elif mode == "informative":
        final_caption = base_caption
    
    else:  # text or fallback
        final_caption = base_caption
    
    is_valid, suggestions = validate_alt_text_wcag(final_caption, context)

    if final_caption and final_caption[-1] not in '.!?':
        final_caption += '.'

    return Response({
        "alt_text": final_caption,
        "mode_applied": mode,
        "character_count": len(final_caption),
        "wcag_compliant": is_valid,
        "suggestions": suggestions if not is_valid else [],
        "model_version": "BLIP-Large-WCAG-2.1-Optimized",
        "wcag_notes": {
            "success_criterion": "1.1.1 Non-text Content (Level A)",
            "guideline": "All non-text content has a text alternative that serves the equivalent purpose"
        }
    })

@api_view(['POST'])
def batch_generate_alt_text(request):
    """
    Generate alt text for multiple images in batch.
    Useful for processing multiple images at once while maintaining WCAG compliance.
    """
    images = request.FILES.getlist('images')
    mode = request.data.get('mode', 'simple')
    
    if not images:
        return Response({"error": "No images provided"}, status=400)
    
    results = []
    
    for idx, image_file in enumerate(images):
        try:
         
            single_request = type('Request', (), {
                'FILES': type('FILES', (), {'get': lambda x: image_file})(),
                'data': {'mode': mode}
            })()
            
          
            response = generate_alt_text(single_request)
            results.append({
                "image_index": idx,
                "filename": image_file.name,
                "result": response.data
            })
        except Exception as e:
            results.append({
                "image_index": idx,
                "filename": image_file.name,
                "error": str(e)
            })
    
    return Response({
        "total_images": len(images),
        "results": results,
        "batch_processing_complete": True
    })