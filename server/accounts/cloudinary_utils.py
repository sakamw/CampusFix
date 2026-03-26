import requests
import os
from django.conf import settings

def upload_image_to_cloudinary(file):
    """
    Upload image to Cloudinary and return the secure URL.
    """
    cloud_name = "dv8k0z6na"
    upload_preset = "newisakrandom"
    
    # upload_preset must be sent as a regular form data field, NOT as a file.
    # The file must be sent in the 'files' dict with its name and content type.
    data = {
        'upload_preset': upload_preset,
    }
    
    # Ensure the file pointer is at the beginning, then read the bytes.
    # Otherwise, subsequent reads might get 0 bytes if DRF already read it.
    file.seek(0)
    file_bytes = file.read()
    
    files = {
        'file': (file.name, file_bytes, file.content_type),
    }
    
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Uploading {file.name} ({file.size} bytes) to Cloudinary")
        response = requests.post(
            f'https://api.cloudinary.com/v1_1/{cloud_name}/image/upload',
            data=data,
            files=files,
        )
        
        if response.status_code == 200:
            result = response.json()
            url = result.get('secure_url')
            logger.info(f"Cloudinary upload success: {url}")
            return url
        else:
            logger.error(f"Cloudinary failed: {response.status_code} - {response.text}")
            raise Exception(f"Cloudinary upload failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Cloudinary network error: {str(e)}")
        raise Exception(f"Network error during Cloudinary upload: {str(e)}")
    except Exception as e:
        logger.error(f"Cloudinary error: {str(e)}")
        raise Exception(f"Error during Cloudinary upload: {str(e)}")
