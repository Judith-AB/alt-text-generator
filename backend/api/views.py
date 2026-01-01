from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image

processor = BlipProcessor.from_pretrained(
    "Salesforce/blip-image-captioning-base"
)
model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base"
)

@api_view(['POST'])
def generate_alt_text(request):
    image_file = request.FILES.get('image')

    if not image_file:
        return Response({"error": "No image provided"}, status=400)

    image = Image.open(image_file).convert("RGB")

    inputs = processor(image, return_tensors="pt")
    output = model.generate(**inputs)
    caption = processor.decode(output[0], skip_special_tokens=True)

    return Response({"alt_text": caption})
