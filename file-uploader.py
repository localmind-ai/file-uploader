import os
import argparse
import logging
import json
from typing import List, Optional, Dict
import mimetypes
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('file_upload.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('file_uploader')

class FileUploader:
    def __init__(self, base_url: str, api_key: str, folder_mapping: Dict[str, str], verify_ssl: bool = False):
        """Initialize the FileUploader with configuration."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.folder_mapping = folder_mapping
        self.verify_ssl = verify_ssl
        self.supported_types = {'.pdf', '.docx', '.txt', '.pptx', '.xlsx'}
        # Define which file types use ultraparse
        self.ultraparse_types = {'.pdf', '.docx', '.pptx'}
        self.headers = {
            'Authorization': f'Bearer {api_key}'
        }

        if not verify_ssl:
            # Disable SSL verification warnings if we're not verifying
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def validate_file(self, file_path: str) -> bool:
        """Validate if the file type is supported and file exists."""
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in self.supported_types:
            logger.error(f"Unsupported file type: {file_extension}")
            return False

        return True

    def upload_file(self, file_path: str, folder_id: str) -> Optional[dict]:
        """Upload a single file to the API."""
        if not self.validate_file(file_path):
            return None

        try:
            url = f"{self.base_url}/localmind/public-upload/file"

            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f,
                                   mimetypes.guess_type(file_path)[0])
                }
                # Determine parser engine based on file type
                file_extension = os.path.splitext(file_path)[1].lower()
                parse_engine = 'ultraparse' if file_extension in self.ultraparse_types else 'tika'

                params = {
                    'folder_id': folder_id,
                    'parse_engine': parse_engine
                }

                logger.info(f"Using parser engine: {parse_engine} for file type: {file_extension}")

                logger.info(f"Starting upload for file: {file_path}")
                response = requests.post(
                    url,
                    files=files,
                    params=params,
                    headers=self.headers,
                    verify=self.verify_ssl  # Add SSL verification parameter
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"Successfully uploaded file: {file_path}")
                logger.debug(f"API Response: {result}")

                return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Upload failed for {file_path}: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Server response: {e.response.text}")
            return None

    def upload_directory(self, local_path: str, folder_id: str) -> List[dict]:
        """Upload all supported files from a specific directory."""
        successful_uploads = []

        if not os.path.isdir(local_path):
            logger.error(f"Directory does not exist: {local_path}")
            return successful_uploads

        logger.info(f"Processing directory: {local_path} with folder ID: {folder_id}")

        for root, _, files in os.walk(local_path):
            for file in files:
                file_path = os.path.join(root, file)
                result = self.upload_file(file_path, folder_id)
                if result:
                    successful_uploads.append(result)

        logger.info(f"Completed uploading {len(successful_uploads)} files from {local_path} successfully")
        return successful_uploads

    def upload_all_mappings(self) -> Dict[str, List[dict]]:
        """Upload files from all directory mappings."""
        results = {}

        for local_path, folder_id in self.folder_mapping.items():
            if os.path.isdir(local_path):
                dir_results = self.upload_directory(local_path, folder_id)
                results[local_path] = dir_results
                logger.info(f"Directory {local_path}: Uploaded {len(dir_results)} files to folder ID {folder_id}")
            else:
                logger.error(f"Directory does not exist: {local_path}")
                results[local_path] = []

        return results

def load_mapping_file(file_path: str) -> Dict[str, str]:
    """Load folder mappings from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            mapping = json.load(f)
        
        # Validate the structure
        for local_path, folder_id in mapping.items():
            if not isinstance(local_path, str) or not isinstance(folder_id, str):
                logger.error(f"Invalid mapping entry: {local_path} -> {folder_id}")
        
        return mapping
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load mapping file: {str(e)}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Upload files from directories to the API')
    parser.add_argument('--base-url', required=True, help='Base URL of the API')
    parser.add_argument('--api-key', required=True, help='API key for authentication')
    
    # Folder mapping options
    mapping_group = parser.add_mutually_exclusive_group(required=True)
    mapping_group.add_argument('--mapping-file', help='JSON file with local directory to folder ID mappings')
    mapping_group.add_argument('--mapping', action='append', nargs=2, metavar=('LOCAL_PATH', 'FOLDER_ID'),
                              help='Map a local directory to a remote folder ID (can be specified multiple times)')
    
    # Single directory upload
    parser.add_argument('--directory', help='Upload a specific local directory')
    parser.add_argument('--folder-id', help='Remote folder ID for the specified directory')
    
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificates')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Load folder mappings from either file or command line arguments
    folder_mapping = {}
    if args.mapping_file:
        folder_mapping = load_mapping_file(args.mapping_file)
        if not folder_mapping:
            logger.error("No valid mappings found in the mapping file.")
            return
    elif args.mapping:
        folder_mapping = {local_path: folder_id for local_path, folder_id in args.mapping}
    
    # Override or add a single directory mapping if specified
    if args.directory and args.folder_id:
        folder_mapping[args.directory] = args.folder_id
    
    if not folder_mapping:
        logger.error("No folder mappings provided.")
        return
    
    logger.info(f"Using folder mappings: {folder_mapping}")
    
    # Create uploader with folder mapping
    uploader = FileUploader(args.base_url, args.api_key, folder_mapping, verify_ssl=args.verify_ssl)

    # Upload files from all mappings
    results = uploader.upload_all_mappings()
    total_files = sum(len(dir_results) for dir_results in results.values())
    logger.info(f"Uploaded a total of {total_files} files from all directories")

if __name__ == "__main__":
    main()
