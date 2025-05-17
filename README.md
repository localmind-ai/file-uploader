# File Uploader for Localmind

This script enables synchronization of documents (PDF, DOCX, TXT, PPTX, XLSX) between local directories or mounted network shares and Localmind via an upload API with configurable folder mappings. It automatically detects added, updated, and deleted files and performs the appropriate operations.

## Features

* Full synchronization between local directories and remote folders
* Automatic detection of added, updated, and deleted files
* Tracking file to monitor file changes across program executions
* Support for multiple file types (PDF, DOCX, TXT, PPTX, XLSX)
* Configurable mapping between local directories and remote folder IDs
* Multiple mapping methods (JSON file, command-line parameters)
* Detailed logging of the synchronization process
* Automatic selection of the appropriate parser engine based on file type

## Requirements

* Python 3.6 or higher
* The following Python packages:
  * requests
  * typing

## Installation

1. Clone this repository or download the file
2. Install the required dependencies:

```bash
pip install requests
```

### Regular Synchronization with Cron Job

Use a cron job to run the script regularly and perform automatic synchronization:

```bash
# Example of a cron job that runs hourly
0 * * * * /usr/bin/python3 /path/to/file-uploader.py --base-url https://your-instance.localmind.url --api-key YOUR_API_KEY --mapping-file /path/to/mappings.json >> /var/log/file_sync.log 2>&1
```

## Troubleshooting

### Resetting the Tracking File

If you want to completely restart synchronization, simply delete the tracking file:

```bash
rm file_tracking.json
```

### Common Issues

1. **File upload fails**:

   * Check the API connection
   * Confirm that the file type is supported
   * Ensure the file is not too large

2. **Missing file IDs in the tracking file**:

   * This can happen if a previous upload failed
   * Delete the tracking file to force a full restart

3. **SSL certificate issues**:

   * Use the `--verify-ssl` option if you are working with a trusted connection
   * For testing, you can skip SSL verification (default behavior)

## Technical Details

### Change Detection

The script uses several methods to detect file changes:

1. First, it checks file size and modification timestamp
2. If these are unchanged, it computes an MD5 hash of the file and compares it to the stored hash
3. Only if all three checks are identical is the file considered unchanged

### Remote API Interactions

The script interacts with the Localmind API via the following endpoints:

* `POST /localmind/public-upload/file`: Upload new files
* `DELETE /localmind/public-upload/files`: Delete files by ID
* `GET /localmind/public-upload/folders/{folder_id}/files`: List files in a folder

## Usage

The script can be configured in various ways to synchronize local directories with remote folders:

### 1. Using a JSON Mapping File

Create a JSON file with mappings between local paths and remote folder IDs:

```json
{
    "/path/to/reports_2023": "aaa44348-f11f-4829-bafc-e68bfeaa8003",
    "/path/to/invoices_2024": "9cf46791-dc7a-4d0c-b3ef-5a6259aa1975"
}
```

Run the script with this mapping file:

```bash
python file-uploader.py --base-url https://your-instance.localmind.url --api-key YOUR_API_KEY --mapping-file mappings.json --tracking-file my_tracking_file.json
```

### 2. Mappings via Command Line

Define mappings directly via the command line:

```bash
python file-uploader.py --base-url https://your-instance.localmind.url --api-key YOUR_API_KEY \
    --mapping /data/presentations b8e941e5-a3e0-43a8-8c8f-778fb92ba4bb /path/to/reports_2023 aaa44348-f11f-4829-bafc-e68bfeaa8003 \
    --mapping /path/to/invoices_2024 9cf46791-dc7a-4d0c-b3ef-5a6259aa1975
```

### 3. Single Directory Mapping

For a single directory:

```bash
python file-uploader.py --base-url https://your-instance.localmind.url --api-key YOUR_API_KEY \
    --directory /path/to/financial_reports --folder-id aaa44348-f11f-4829-bafc-e68bfeaa8003
```

## Additional Parameters

* `--tracking-file`: Path to the JSON file for tracking file changes (default: file\_tracking.json)
* `--verbose`: Enables verbose logging
* `--verify-ssl`: Checks SSL certificates (disabled by default)

## Logging and Tracking

The script creates the following files in the current directory:

* `file_upload.log`: Contains detailed information about the synchronization process
* `file_tracking.json` (or specified tracking file): Stores information about synchronized files to detect changes

## Parser Engines

* `ultraparse`: Used for PDF, DOCX, and PPTX
* `tika`: Used for other supported formats

## Troubleshooting

If you encounter problems, check:

1. Whether the API base URL and API key are correct
2. Whether the specified local directories exist
3. The log file for detailed error messages

## How Synchronization Works

1. **Tracking File**: The script uses a JSON file to store the state of all synchronized files
2. **Change Detection**: On each run, the following checks are performed:

   * File size
   * Modification timestamp
   * MD5 hash of the file contents
3. **Synchronization Process**:

   * **New files**: Are uploaded and added to the tracking file
   * **Changed files**: The old version is deleted and the new one uploaded
   * **Deleted files**: Are also deleted from the remote folder
   * **Unchanged files**: Are skipped to save bandwidth

## Example Use Cases

### Synchronizing Annual Reports

```bash
python file-uploader.py --base-url https://your-instance.localmind.url --api-key YOUR_API_KEY \
    --mapping /data/reports/2023 aaa44348-f11f-4829-bafc-e68bfeaa8003 \
    --mapping /data/reports/2024 9cf46791-dc7a-4d0c-b3ef-5a6259aa1975
```

### Synchronizing Different Document Types into Different Folders

```bash
python file-uploader.py --base-url https://your-instance.localmind.url --api-key YOUR_API_KEY \
    --mapping /data/invoices f8c47ef2-b0e4-4f0b-bda6-725a263b2509 \
    --mapping /data/contracts d837154b-4513-4f67-81c3-99c4409e1d18 \
    --mapping ...
```
