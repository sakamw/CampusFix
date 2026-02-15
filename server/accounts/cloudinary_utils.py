import requests
import os
from django.conf import settings

def upload_image_to_cloudinary(file):
    """
    Upload image to Cloudinary and return the secure URL.
    """
    cloud_name = "dv8k0z6na"
    upload_preset = "newisakrandom"
    
    # Prepare the file for upload
    files = {
        'file': file,
        'upload_preset': upload_preset
    }
    
    try:
        response = requests.post(
            f'https://api.cloudinary.com/v1_1/{cloud_name}/image/upload',
            files=files
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('secure_url')
        else:
            raise Exception(f"Cloudinary upload failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error during Cloudinary upload: {str(e)}")
    except Exception as e:
        raise Exception(f"Error during Cloudinary upload: {str(e)}")
