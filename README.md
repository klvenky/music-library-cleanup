# Music Metadata Fixer

## Disclaimer

This is vibe-coded with Cursor & maynot work otherwise.

A powerful Python script to clean up music file names and metadata by removing leading numbers, website details, and trailing spaces. The script processes music files recursively through directories and provides comprehensive logging and error handling.

## How It Works

The script uses a multi-pass approach to ensure complete cleaning:

1. **Initial Scan**: Processes all music files in the directory and subdirectories
2. **Pattern Detection**: Identifies files that need cleaning based on the specified rules
3. **Multi-Pass Processing**: Continues processing until no more patterns are found to replace
4. **Safety Limit**: Stops after 10 passes to prevent infinite loops
5. **Complete Results**: Ensures all possible cleaning operations are completed

This approach handles complex cases where initial cleaning creates new patterns that need to be cleaned in subsequent passes.

## Features

- **Recursive Processing**: Automatically processes all music files in subdirectories
- **Multi-Pass Cleaning**: Runs recursively until no more patterns are found to replace
- **Leading Number Removal**: Removes numbers, dashes, underscores, dots, spaces, and square brackets at the beginning of filenames
- **Website Detail Cleanup**: Removes URLs, domain names, and website references from filenames
- **URL Tracking**: Tracks and displays a unique list of all URLs that were replaced during processing
- **Bracket Cleanup**: Removes trailing square brackets and their content, as well as empty brackets
- **Whitespace Normalization**: Normalizes multiple spaces and removes leading/trailing whitespace
- **Unicode Normalization**: Normalizes unicode characters and removes invalid filename characters
- **Metadata Cleaning**: Cleans ID3 tags, Vorbis comments, ASF tags, and MP4 tags
- **Album Organization**: Moves files from "singles" folders into album folders based on metadata
- **Dry Run Mode**: Preview changes without actually modifying files
- **Comprehensive Logging**: Detailed logging with different verbosity levels
- **Error Handling**: Robust error handling with detailed error messages
- **Multiple Audio Formats**: Supports MP3, FLAC, OGG, WAV, M4A, and WMA files

## Quick Start

### Installation

```bash
# Install dependencies
make install

# Or manually
pip install mutagen
```

### Basic Usage

```bash
# Show available operations
make help

# Preview file renaming (recommended first step)
make rename-dry-run DIRECTORY=/path/to/your/music

# Actually rename files
make rename DIRECTORY=/path/to/your/music

# Clean metadata only
make metadata DIRECTORY=/path/to/your/music

# Organize albums
make albums DIRECTORY=/path/to/your/music

# Run all operations
make all DIRECTORY=/path/to/your/music
```

### Testing

```bash
# Create test files
make test

# Test the renaming on sample files
make rename-dry-run DIRECTORY=test_music

# Clean up test files
make clean
```

## Available Operations

### File Renaming
- `make rename DIRECTORY=/path/to/music` - Rename music files with recursive cleaning
- `make rename-dry-run DIRECTORY=/path/to/music` - Preview renaming without making changes

### Metadata Cleaning
- `make metadata DIRECTORY=/path/to/music` - Clean metadata tags in music files
- `make metadata-dry-run DIRECTORY=/path/to/music` - Preview metadata cleaning

### Album Organization
- `make albums DIRECTORY=/path/to/music` - Organize music files into album folders
- `make albums-dry-run DIRECTORY=/path/to/music` - Preview album organization

**Note:** The album mapper now works with any directory containing music files, not just "singles" folders. It will organize files into album folders based on metadata, but only if the album contains more than 3 songs.

### Combined Operations
- `make all DIRECTORY=/path/to/music` - Run all operations (rename + metadata + albums)
- `make all-dry-run DIRECTORY=/path/to/music` - Preview all operations

### Utility
- `make install` - Install required dependencies
- `make test` - Create test files for experimentation
- `make clean` - Remove test files and logs

## Supported File Formats

- **Audio Files**: MP3, FLAC, OGG, WAV, M4A, WMA, AAC, OPUS, ALAC, AIFF, DSD (.dsd, .dff, .dsf)
- **Metadata Formats**: ID3 (MP3), Vorbis Comments (FLAC, OGG), ASF (WMA), MP4 (M4A)

## What Gets Cleaned

### Filename Cleaning
- Removes leading numbers, dashes, underscores, dots, spaces, and square brackets
- Removes website details (URLs, domain names, website references)
- Removes trailing square brackets and their content
- Removes empty brackets
- Normalizes multiple spaces to single spaces
- Removes leading and trailing whitespace
- Normalizes unicode characters
- Removes invalid filename characters

### URL Tracking
- Tracks all unique URLs and domain names that are removed during processing
- Displays a comprehensive list of replaced URLs in the final statistics
- Works for both filename and metadata cleaning
- Helps identify common sources of music files
- Generates a detailed markdown report with filename changes table

### Markdown Report
- Generates a comprehensive markdown report (`outputs/replaced_urls_YYYY-MM-DD_HH-MM-SS.md`)
- Includes a table showing original vs final filenames after all recursions
- Lists all unique URLs that were replaced during processing
- Provides processing statistics and summary
- Shows directory paths for each file change
- Includes dry-run indicators when applicable

### Metadata Cleaning
- Cleans title, artist, and album tags using the same rules as filename cleaning
- Supports multiple metadata formats (ID3, Vorbis, ASF, MP4)
- Preserves other metadata tags

### Album Organization
- Moves files from any directory into album folders
- Creates album folders named `${album name} (${year})` based on metadata
- Handles missing year information gracefully
- Resolves filename conflicts automatically
- Only moves files if the album contains more than 3 songs
- Avoids duplicating year in folder name if already present in album name
- Supports all major audio formats (MP3, FLAC, OGG, WMA, M4A, WAV, AAC, OPUS, ALAC, AIFF, DSD)
- Provides comprehensive logging and statistics

## Examples

### Before and After Filenames

```
Before: "01 - [2023] Artist - Song [Remix] [].mp3"
After:  "Artist - Song.mp3"

Before: "123_www.example.com_Track [Live] [].flac"
After:  "Track.flac"

Before: "  05-Artist-Song  [].wav"
After:  "Artist-Song.wav"
```

### Album Organization Examples

| File Metadata | Created Folder | Notes |
|---------------|----------------|-------|
| Album: "Dark Side of the Moon", Year: "1973" | `Dark Side of the Moon (1973)` | Year added |
| Album: "Greatest Hits (2020)", Year: "2020" | `Greatest Hits (2020)` | Year not duplicated |
| Album: "Unknown Album", Year: "" | `Unknown Album` | No year available |
| Album: "Live at Wembley", Year: "1995" | `Live at Wembley (1995)` | Year added |

**Note**: Only albums with more than 3 songs are organized into folders.

### Sample Output

```
2024-01-15 10:30:15,123 - INFO - Processing directory: /path/to/music
2024-01-15 10:30:15,124 - INFO - Starting pass 1...
2024-01-15 10:30:15,125 - INFO - Pass 1 completed: 45 changes made
2024-01-15 10:30:15,126 - INFO - Starting pass 2...
2024-01-15 10:30:15,127 - INFO - Pass 2 completed: 12 changes made
2024-01-15 10:30:15,128 - INFO - Starting pass 3...
2024-01-15 10:30:15,129 - INFO - Pass 3 completed: No changes needed
2024-01-15 10:30:15,130 - INFO - Processing completed after 3 passes with 57 total changes
2024-01-15 10:30:15,131 - INFO - ==================================================
2024-01-15 10:30:15,132 - INFO - PROCESSING STATISTICS
2024-01-15 10:30:15,133 - INFO - ==================================================
2024-01-15 10:30:15,134 - INFO - Total files processed: 150
2024-01-15 10:30:15,135 - INFO - Files renamed: 45
2024-01-15 10:30:15,136 - INFO - Files with metadata updated: 12
2024-01-15 10:30:15,137 - INFO - Files skipped (no changes): 93
2024-01-15 10:30:15,138 - INFO - Errors encountered: 0
2024-01-15 10:30:15,139 - INFO - ==================================================
2024-01-15 10:30:15,140 - INFO - UNIQUE URLS REPLACED
2024-01-15 10:30:15,141 - INFO - ==================================================
2024-01-15 10:30:15,142 - INFO -   - example.com
2024-01-15 10:30:15,143 - INFO -   - music.site.org
2024-01-15 10:30:15,144 - INFO -   - spotify.com
2024-01-15 10:30:15,145 - INFO -   - www.download.com
2024-01-15 10:30:15,146 - INFO -   - youtube.com
2024-01-15 10:30:15,147 - INFO - Total unique URLs replaced: 5
2024-01-15 10:30:15,148 - INFO - ==================================================
2025-06-29 05:54:06,076 - INFO - Total unique URLs replaced: 4
2025-06-29 05:54:06,076 - INFO - Report written to: replaced_urls_2025-06-29_05-54-06.md
2025-06-29 05:54:06,076 - INFO - DRY RUN MODE - No files were actually renamed or modified
2025-06-29 05:54:06,076 - INFO - ==================================================
```

## Requirements

- Python 3.6 or higher
- mutagen library (for metadata editing)

## Installation

```bash
# Clone or download the repository
git clone <repository-url>
cd music-metadata-fixer

# Install dependencies
make install
```

## Advanced Usage

### Direct Python Script Usage

If you prefer to use the Python scripts directly:

```bash
# File renaming
python3 music_renamer.py /path/to/music --dry-run --verbose

# Metadata cleaning only
python3 music_renamer.py /path/to/music --metadata-only --dry-run --verbose

# Album organization
python3 album_mapper.py /path/to/music --dry-run --verbose
```

### Command Line Options

#### music_renamer.py
- `--dry-run`: Preview changes without making them
- `--verbose`: Enable detailed logging
- `--metadata-only`: Only clean metadata, skip filename cleaning
- `--filename-only`: Only clean filenames, skip metadata cleaning

#### album_mapper.py
- `--dry-run`: Preview changes without making them
- `--verbose`: Enable detailed logging
- `--remove-empty`: Remove empty "singles" folders after moving files

## Safety Features

- **Dry Run Mode**: Always preview changes before applying them
- **Backup Recommendation**: Back up your music collection before running the script
- **Conflict Resolution**: Automatically handles filename conflicts
- **Error Handling**: Continues processing even if individual files fail
- **Logging**: Comprehensive logging for audit trails

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure you have write permissions to the music directory
2. **Missing Dependencies**: Run `make install` to install required packages
3. **Unsupported Files**: The script only processes supported audio formats
4. **Metadata Errors**: Some files may have corrupted or unsupported metadata

### Getting Help

1. Always run with `--dry-run` first to preview changes
2. Use `--verbose` for detailed logging
3. Check the log files for specific error messages
4. Test on a small subset of files first

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the script.

## License

This project is open source and available under the MIT License. 