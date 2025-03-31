import os
import argparse
import logging
import json
import hashlib
import time
from typing import List, Optional, Dict, Set
import mimetypes
import requests
from pathlib import Path
from datetime import datetime

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

class FileTracker:
    """Track file changes between syncs."""
    
    def __init__(self, tracking_file: str = "file_tracking.json"):
        """Initialize with tracking file path."""
        self.tracking_file = tracking_file
        self.tracking_data = self._load_tracking_data()
    
    def _load_tracking_data(self) -> Dict:
        """Load tracking data from file or initialize empty dict."""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Invalid tracking file format: {self.tracking_file}")
                return {}
        return {}
    
    def _save_tracking_data(self):
        """Save tracking data to file."""
        with open(self.tracking_file, 'w') as f:
            json.dump(self.tracking_data, f, indent=2)
    
    def compute_file_hash(self, file_path: str) -> Optional[str]:
        """Compute MD5 hash of file content."""
        try:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                # Read file in chunks for memory efficiency
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {str(e)}")
            return None
    
    def get_file_metadata(self, file_path: str) -> Optional[Dict]:
        """Get file metadata including size, modification time, and hash."""
        try:
            stat = os.stat(file_path)
            return {
                "path": file_path,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "hash": self.compute_file_hash(file_path)
            }
        except Exception as e:
            logger.error(f"Error getting metadata for {file_path}: {str(e)}")
            return None
    
    def update_file_tracking(self, local_path: str, file_id: str, file_metadata: Dict):
        """Update tracking data for a file."""
        if local_path not in self.tracking_data:
            self.tracking_data[local_path] = {}
        
        self.tracking_data[local_path][file_metadata["path"]] = {
            "file_id": file_id,
            "size": file_metadata["size"],
            "mtime": file_metadata["mtime"],
            "hash": file_metadata["hash"],
            "last_synced": time.time()
        }
        self._save_tracking_data()
    
    def remove_file_tracking(self, local_path: str, file_path: str):
        """Remove a file from tracking data."""
        if local_path in self.tracking_data and file_path in self.tracking_data[local_path]:
            del self.tracking_data[local_path][file_path]
            self._save_tracking_data()
    
    def is_file_changed(self, local_path: str, file_path: str, file_metadata: Dict) -> bool:
        """Check if file has changed since last sync."""
        if local_path not in self.tracking_data or file_path not in self.tracking_data[local_path]:
            return True  # New file
        
        tracked_data = self.tracking_data[local_path][file_path]
        
        # First check quick metadata (size and mtime)
        if tracked_data["size"] != file_metadata["size"] or tracked_data["mtime"] != file_metadata["mtime"]:
            logger.debug(f"File {file_path} changed: size/mtime differs")
            logger.debug(f"  Tracked: size={tracked_data['size']}, mtime={tracked_data['mtime']}")
            logger.debug(f"  Current: size={file_metadata['size']}, mtime={file_metadata['mtime']}")
            return True
        
        # If metadata matches but hash differs, file content has changed
        if tracked_data["hash"] != file_metadata["hash"]:
            logger.debug(f"File {file_path} changed: hash differs")
            logger.debug(f"  Tracked hash: {tracked_data['hash']}")
            logger.debug(f"  Current hash: {file_metadata['hash']}")
            return True
        
        logger.debug(f"File {file_path} unchanged")
        return False
    
    def get_tracked_files(self, local_path: str) -> Set[str]:
        """Get set of tracked files for a local path."""
        if local_path in self.tracking_data:
            return set(self.tracking_data[local_path].keys())
        return set()
    
    def get_file_id(self, local_path: str, file_path: str) -> Optional[str]:
        """Get remote file ID for a tracked file."""
        if local_path in self.tracking_data and file_path in self.tracking_data[local_path]:
            return self.tracking_data[local_path][file_path]["file_id"]
        return None


class FileUploader:
    def __init__(self, base_url: str, api_key: str, folder_mapping: Dict[str, str], 
                 tracker: FileTracker, verify_ssl: bool = False):
        """Initialize the FileUploader with configuration."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.folder_mapping = folder_mapping
        self.tracker = tracker
        self.verify_ssl = verify_ssl
        self.supported_types = {'.pdf', '.docx', '.txt', '.pptx', '.xlsx'}
        # Define which file types use ultraparse
        self.ultraparse_types = {'.pdf', '.docx', '.pptx'}
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
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

    def upload_file(self, file_path: str, folder_id: str) -> Optional[str]:
        """Upload a single file to the API. Returns the file ID if successful."""
        if not self.validate_file(file_path):
            return None

        try:
            # Check if file with same name already exists on remote
            filename = os.path.basename(file_path)
            remote_files = self.list_remote_files(folder_id)
            
            # If file already exists, return its ID
            if filename in remote_files:
                file_id = remote_files[filename]
                logger.info(f"File already exists remotely: {filename}, ID: {file_id}")
                return file_id
                
            url = f"{self.base_url}/localmind/public-upload/file"

            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, mimetypes.guess_type(file_path)[0])
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
                    verify=self.verify_ssl
                )

                response.raise_for_status()
                result = response.json()
                
                # Extract file ID from response - API might return ID directly or in a data structure
                file_id = None
                if isinstance(result, dict):
                    file_id = result.get("id")
                elif isinstance(result, str):
                    # Some APIs return just the ID as a string
                    file_id = result
                
                if not file_id:
                    # Look for ID in other common response formats
                    if isinstance(result, dict) and "data" in result and isinstance(result["data"], dict):
                        file_id = result["data"].get("id")
                
                if not file_id and "status" in result:
                    # The API appears to be returning a status but not a clear ID
                    # This is a special case to handle the response format shown in logs
                    logger.info(f"File appears to be uploaded successfully, but no clear ID was found")
                    
                    # Wait briefly for the server to process the upload
                    time.sleep(1)
                    
                    # Try to find the file by listing files again
                    updated_remote_files = self.list_remote_files(folder_id)
                    if filename in updated_remote_files:
                        file_id = updated_remote_files[filename]
                        logger.info(f"Retrieved file ID after upload: {file_id}")
                
                if file_id:
                    logger.info(f"Successfully uploaded file: {file_path}, ID: {file_id}")
                else:
                    logger.warning(f"No file ID found in response for {file_path}: {result}")
                    
                logger.debug(f"API Response: {result}")
                return file_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Upload failed for {file_path}: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Server response: {e.response.text}")
            return None

    def delete_file(self, file_id: str, folder_id: str) -> bool:
        """Delete a file from the remote system."""
        try:
            url = f"{self.base_url}/localmind/public-upload/files"
            
            params = {
                'folder_id': folder_id
            }
            
            data = {
                'file_ids': [file_id]
            }
            
            logger.info(f"Deleting file with ID: {file_id}")
            response = requests.delete(
                url,
                json=data,
                params=params,
                headers=self.headers,
                verify=self.verify_ssl
            )
            
            response.raise_for_status()
            logger.info(f"Successfully deleted file with ID: {file_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Delete failed for file ID {file_id}: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Server response: {e.response.text}")
            return False

    def list_remote_files(self, folder_id: str) -> Dict[str, str]:
        """List files in a remote folder. Returns a dict of filename to file ID."""
        try:
            url = f"{self.base_url}/localmind/public-upload/folders/{folder_id}/files"
            
            logger.info(f"Listing files in folder ID: {folder_id}")
            response = requests.get(
                url,
                headers=self.headers,
                verify=self.verify_ssl
            )
            
            response.raise_for_status()
            result = response.json()
            
            files_dict = {}
            for file_info in result.get("data", []):
                file_id = file_info.get("id")
                file_name = file_info.get("name")
                if file_id and file_name:
                    files_dict[file_name] = file_id
            
            logger.info(f"Found {len(files_dict)} files in folder ID: {folder_id}")
            return files_dict
            
        except requests.exceptions.RequestException as e:
            logger.error(f"List files failed for folder ID {folder_id}: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Server response: {e.response.text}")
            # Return empty dict instead of failing - this allows uploads to continue
            return {}

    def sync_directory(self, local_path: str, folder_id: str) -> Dict:
        """
        Synchronize a local directory with a remote folder.
        
        Performs these operations:
        1. Upload new files
        2. Update changed files (delete + upload)
        3. Delete files that no longer exist locally
        
        Returns statistics about operations performed.
        """
        if not os.path.isdir(local_path):
            logger.error(f"Directory does not exist: {local_path}")
            return {"error": f"Directory does not exist: {local_path}"}

        logger.info(f"Syncing directory: {local_path} with folder ID: {folder_id}")
        
        # Track statistics
        stats = {
            "added": 0,
            "updated": 0,
            "deleted": 0,
            "skipped": 0,
            "failed": 0
        }
        
        # Fetch remote files first
        remote_files_dict = self.list_remote_files(folder_id)
        remote_filenames = set(remote_files_dict.keys())
        logger.info(f"Found {len(remote_filenames)} files in remote folder {folder_id}")
        
        # Get current files in directory
        current_files = set()
        local_filenames_map = {}  # Maps filename -> full path
        
        for root, _, files in os.walk(local_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                if self.validate_file(file_path):
                    current_files.add(file_path)
                    # Map the basename to full path for later lookups
                    local_filenames_map[os.path.basename(file_path)] = file_path
        
        # Get previously tracked files
        tracked_files = self.tracker.get_tracked_files(local_path)
        
        # Get local filenames (basenames only)
        local_filenames = set(os.path.basename(f) for f in current_files)
        
        # Identify files by name comparison
        new_file_names = local_filenames - remote_filenames
        existing_file_names = local_filenames.intersection(remote_filenames)
        deleted_file_names = remote_filenames - local_filenames
        
        # Process new files (upload)
        for filename in new_file_names:
            file_path = local_filenames_map[filename]
            metadata = self.tracker.get_file_metadata(file_path)
            if not metadata:
                logger.error(f"Failed to get metadata for {file_path}")
                stats["failed"] += 1
                continue
                
            file_id = self.upload_file(file_path, folder_id)
            if file_id:
                self.tracker.update_file_tracking(local_path, file_id, metadata)
                stats["added"] += 1
                logger.info(f"Successfully added file: {file_path}")
            else:
                # Special handling for the case where upload succeeds but we don't get an ID
                # Check if the file now exists remotely
                updated_remote_files = self.list_remote_files(folder_id)
                if filename in updated_remote_files and filename not in remote_filenames:
                    # File was actually uploaded successfully
                    file_id = updated_remote_files[filename]
                    self.tracker.update_file_tracking(local_path, file_id, metadata)
                    stats["added"] += 1
                    logger.info(f"Successfully added file (verified after upload): {file_path}")
                else:
                    stats["failed"] += 1
        
        # Process existing files (check for changes)
        for filename in existing_file_names:
            file_path = local_filenames_map[filename]
            metadata = self.tracker.get_file_metadata(file_path)
            if not metadata:
                logger.error(f"Failed to get metadata for {file_path}")
                stats["failed"] += 1
                continue
            
            # Get the remote file ID
            remote_file_id = remote_files_dict[filename]
            
            # Update tracking data with the remote ID if not already tracked
            if file_path not in tracked_files:
                self.tracker.update_file_tracking(local_path, remote_file_id, metadata)
                stats["skipped"] += 1
                logger.info(f"File already exists remotely, updated tracking: {file_path}")
                continue
                
            if self.tracker.is_file_changed(local_path, file_path, metadata):
                # File changed, delete old version and upload new
                if self.delete_file(remote_file_id, folder_id):
                    # Upload new version
                    new_file_id = self.upload_file(file_path, folder_id)
                    if new_file_id:
                        self.tracker.update_file_tracking(local_path, new_file_id, metadata)
                        stats["updated"] += 1
                        logger.info(f"Successfully updated file: {file_path}")
                    else:
                        stats["failed"] += 1
                else:
                    stats["failed"] += 1
            else:
                # Make sure tracking data has the correct remote ID
                old_file_id = self.tracker.get_file_id(local_path, file_path)
                if old_file_id != remote_file_id:
                    self.tracker.update_file_tracking(local_path, remote_file_id, metadata)
                    logger.info(f"Updated tracking with correct remote ID for: {file_path}")
                
                # File unchanged
                stats["skipped"] += 1
                logger.info(f"Skipped unchanged file: {file_path}")
        
        # Process deleted files
        for filename in deleted_file_names:
            file_id = remote_files_dict[filename]
            if self.delete_file(file_id, folder_id):
                # Find and remove from tracking if it exists
                deleted_paths = [p for p in tracked_files if os.path.basename(p) == filename]
                for path in deleted_paths:
                    self.tracker.remove_file_tracking(local_path, path)
                stats["deleted"] += 1
                logger.info(f"Successfully deleted remote file: {filename}")
            else:
                stats["failed"] += 1
        
        logger.info(f"Directory sync complete for {local_path}. Stats: {stats}")
        return stats

    def sync_all_mappings(self) -> Dict[str, Dict]:
        """Synchronize all directory mappings."""
        results = {}

        for local_path, folder_id in self.folder_mapping.items():
            if os.path.isdir(local_path):
                dir_results = self.sync_directory(local_path, folder_id)
                results[local_path] = dir_results
                logger.info(f"Directory {local_path}: Sync completed with folder ID {folder_id}")
            else:
                logger.error(f"Directory does not exist: {local_path}")
                results[local_path] = {"error": "Directory does not exist"}

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
    parser = argparse.ArgumentParser(description='Sync files between local directories and remote API')
    parser.add_argument('--base-url', required=True, help='Base URL of the API')
    parser.add_argument('--api-key', required=True, help='API key for authentication')
    
    # Folder mapping options
    mapping_group = parser.add_mutually_exclusive_group(required=True)
    mapping_group.add_argument('--mapping-file', help='JSON file with local directory to folder ID mappings')
    mapping_group.add_argument('--mapping', action='append', nargs=2, metavar=('LOCAL_PATH', 'FOLDER_ID'),
                              help='Map a local directory to a remote folder ID (can be specified multiple times)')
    
    # Single directory sync
    parser.add_argument('--directory', help='Sync a specific local directory')
    parser.add_argument('--folder-id', help='Remote folder ID for the specified directory')
    
    # Tracking file
    parser.add_argument('--tracking-file', default='file_tracking.json',
                       help='JSON file to track file changes (default: file_tracking.json)')
    
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
    
    # Initialize file tracker
    tracker = FileTracker(args.tracking_file)
    
    # Create uploader with folder mapping
    uploader = FileUploader(args.base_url, args.api_key, folder_mapping, tracker, verify_ssl=args.verify_ssl)

    # Sync files from all mappings
    results = uploader.sync_all_mappings()
    
    # Calculate totals
    total_added = sum(result.get("added", 0) for result in results.values())
    total_updated = sum(result.get("updated", 0) for result in results.values())
    total_deleted = sum(result.get("deleted", 0) for result in results.values())
    total_skipped = sum(result.get("skipped", 0) for result in results.values())
    total_failed = sum(result.get("failed", 0) for result in results.values())
    
    logger.info(f"Sync summary: Added {total_added}, Updated {total_updated}, " +
                f"Deleted {total_deleted}, Skipped {total_skipped}, Failed {total_failed}")


if __name__ == "__main__":
    main()
