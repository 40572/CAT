import os
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

import os
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

azure_openai_vision_endpoint = "https://ussvcconsultin7275365216.cognitiveservices.azure.com/"
azure_openai_vision_key = "1Y285NfntyOJBj0CQmmyMGWaUCP3pf1AEtRvEqZ0nwIA1P7vwZeKJQQJ99AKACYeBjFXJ3w3AAAAACOGkzWH"

def analyze_image_text(target_image): 
    # Create an Image Analysis client
    image_has_text = False

    client = ImageAnalysisClient(
        endpoint=azure_openai_vision_endpoint,
        credential=AzureKeyCredential(azure_openai_vision_key)
    )

    result = client.analyze(
        image_data = target_image,
        visual_features=[VisualFeatures.CAPTION, VisualFeatures.READ],
        gender_neutral_caption=True,  # Optional (default is False)
        )
    if result.read is not None:
            image_has_text = True
    return image_has_text
