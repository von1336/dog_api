# Dog Images Downloader for Yandex.Disk

Automated GUI application for downloading dog breed images from dog.ceo API to Yandex.Disk cloud storage with organized folder structure.

## Project Overview

This application retrieves all available dog breeds from the dog.ceo API and downloads one representative image for each breed or sub-breed. Images are uploaded directly to Yandex.Disk without local storage using remote upload capabilities.

## Features

- Modern graphical interface built with CustomTkinter
- Real-time progress monitoring and statistics
- Integrated logging with export capabilities
- Token management with secure storage
- Results viewer with export functionality
- Automatic configuration saving

## System Requirements

- Python 3.7 or higher
- Yandex.Disk API OAuth token
- Internet connection for API access
- Tkinter support for GUI version (included with most Python installations)

## Installation

1. Clone or download the project files
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Obtaining Yandex.Disk API Token

1. Visit [Yandex OAuth](https://oauth.yandex.ru/)
2. Register a new application
3. Grant "Yandex.Disk REST API" permissions
4. Obtain OAuth token with write permissions

### Token Setup

**Option 1: Environment Variable (Recommended)**
```bash
# Windows
set YANDEX_DISK_TOKEN=your_token_here

# Linux/macOS
export YANDEX_DISK_TOKEN=your_token_here
```

**Option 2: Direct Configuration**
Modify the token value in `config.py` or GUI interface.

## Usage

### Running the Application
```bash
python dog_images_gui.py
```
Or execute the batch file:
```bash
run_gui.bat
```

### First Time Setup
1. Launch the application
2. Enter your Yandex.Disk OAuth token in the token field
3. Configure the folder name (optional, defaults to "DogImages")
4. Click "Check Token" to verify your credentials
5. Click "Start Download" to begin the process

Your settings will be automatically saved for future use.

## Output Structure

### Yandex.Disk Folder Organization
```
DogImages/
├── affenpinscher/
│   └── affenpinscher_n02110627_8534.jpg
├── spaniel/
│   ├── spaniel_blenheim_n02086646_1870.jpg
│   ├── spaniel_brittany_n02101388_5028.jpg
│   ├── spaniel_cocker_n02102318_3857.jpg
│   └── spaniel_irish_n02102973_3733.jpg
└── [other_breeds]/
```

### Results JSON Structure
```json
{
  "metadata": {
    "created_at": "2024-01-15T10:30:00",
    "total_images": 150,
    "successful_uploads": 145,
    "failed_uploads": 5
  },
  "results": [
    {
      "breed": "spaniel",
      "sub_breed": "irish",
      "breed_full_name": "spaniel_irish",
      "source_url": "https://images.dog.ceo/breeds/spaniel-irish/n02102973_3733.jpg",
      "filename": "spaniel_irish_n02102973_3733.jpg",
      "disk_path": "/DogImages/spaniel/spaniel_irish_n02102973_3733.jpg",
      "upload_status": "success",
      "upload_info": {
        "disk_path": "/DogImages/spaniel/spaniel_irish_n02102973_3733.jpg",
        "source_url": "https://images.dog.ceo/breeds/spaniel-irish/n02102973_3733.jpg",
        "status": "uploaded_remote",
        "method": "remote_upload"
      },
      "timestamp": "2024-01-15T10:31:25"
    }
  ]
}
```

## Project Architecture

### File Structure
```
project/
├── dog_images_gui.py         # Complete GUI application (all-in-one)
├── requirements.txt          # Python dependencies
├── run_gui.bat              # Application launcher
├── README.md                # Project documentation
├── .gitignore               # Git exclusions
└── app_config.json          # User settings (auto-generated)
```

## Technical Implementation

### Breed Processing Logic
- **Breeds without sub-breeds:** Download one random image
- **Breeds with sub-breeds:** Download one image per sub-breed
- **Naming convention:** `{breed}_{sub_breed}_{original_filename}.jpg`

### Upload Mechanism
The application uses Yandex.Disk's remote upload feature:
1. Obtain upload URL from Yandex.Disk API
2. Stream image data directly from dog.ceo to Yandex.Disk
3. No local file storage required

### Error Handling
- Comprehensive logging with configurable levels
- Graceful degradation for failed uploads
- Network timeout management
- API response validation

### GUI Features
- **Dark theme interface** with modern design
- **Real-time logging** displayed in application
- **Progress tracking** with detailed status updates
- **Token management** with visibility controls
- **Statistics monitoring** showing current progress
- **Multithreading** to prevent UI blocking
- **Export capabilities** for logs and results

## Configuration Options

### Environment Variables
- `YANDEX_DISK_TOKEN`: OAuth token for Yandex.Disk access

### Configurable Parameters
- `BASE_FOLDER_NAME`: Root folder name on Yandex.Disk
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

### Configuration Storage
The application automatically saves your settings in `app_config.json`:
- Yandex.Disk OAuth token (securely stored locally)
- Preferred folder name for uploads
- Configuration is loaded automatically on application restart

## Dependencies

- `requests`: HTTP client for API communication
- `customtkinter`: Modern GUI framework

## API Compliance

### dog.ceo API
- Retrieves breed list from `/breeds/list/all` endpoint
- Fetches random images using `/breed/{breed}/images/random`
- Handles sub-breed requests via `/breed/{breed}/{sub-breed}/images/random`

### Yandex.Disk API
- Uses OAuth authentication with write permissions
- Creates folder structure via `/resources` endpoint
- Uploads files using remote upload method
- Implements proper error handling and status codes

## Performance Considerations

- **Remote uploads** eliminate local storage requirements
- **Concurrent processing** for improved throughput
- **Memory-efficient** streaming of image data
- **Graceful degradation** for network issues

## Logging and Monitoring

The application provides comprehensive logging:
- **File logging:** Detailed logs saved to disk
- **Console output:** Real-time status updates
- **GUI integration:** Live log display in application
- **Debug mode:** Verbose API interaction details

## Error Recovery

- **Token validation** before processing begins
- **Folder creation verification** with conflict resolution
- **Upload retry logic** with fallback mechanisms
- **Partial completion** support with result persistence

## Security Considerations

- Token handling with environment variable support
- No sensitive data in source code (when properly configured)
- Secure API communication over HTTPS
- Input validation for all user-provided data

## License

This project is developed for educational and demonstration purposes. 