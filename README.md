# Music Metadata Fixer

## Disclaimer

This is vibe-coded with Cursor & maynot work otherwise.

A powerful Python script to clean up music file names and metadata by removing leading numbers, website details, and trailing spaces. The script processes music files recursively through directories and provides comprehensive logging and error handling.

## Features

- **Recursive Processing**: Automatically processes all music files in subdirectories
- **Leading Number Removal**: Removes numbers, dashes, underscores, dots, spaces, and square brackets at the beginning of filenames
- **Website Detail Cleanup**: Removes URLs, domain names, and website references from filenames
- **Trailing Bracket Removal**: Removes trailing square brackets and their content from filenames
- **Empty Bracket Removal**: Removes any remaining empty brackets from filenames
- **Space Normalization**: Normalizes multiple spaces and whitespace characters throughout the filename
- **Metadata Cleaning**: Cleans up ID3 tags and other metadata with the same rules as filenames
- **Unicode Normalization**: Handles special characters and unicode normalization
- **Conflict Resolution**: Automatically handles filename conflicts by adding numbers
- **Dry Run Mode**: Preview changes without actually renaming files or modifying metadata
- **Comprehensive Logging**: Detailed logs with both file and console output
- **Error Handling**: Robust error handling with detailed error messages

## Supported File Formats

The script supports the following music file formats:
- MP3 (.mp3)
- FLAC (.flac)
- WAV (.wav)
- AAC (.aac)
- OGG (.ogg)
- M4A (.m4a)
- WMA (.wma)
- OPUS (.opus)
- ALAC (.alac)
- AIFF (.aiff)
- DSD (.dsd, .dff, .dsf)

## Installation

1. Clone or download this repository
2. Ensure Python 3.6+ is installed on your system
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Make the shell script executable (optional):
   ```bash
   chmod +x rename_music.sh
   ```

## Usage

### Using the Python Script Directly

```bash
# Basic usage (process current directory)
python3 music_renamer.py

# Process a specific directory
python3 music_renamer.py /path/to/music/folder

# Dry run mode (preview changes without renaming)
python3 music_renamer.py /path/to/music/folder --dry-run

# Verbose logging
python3 music_renamer.py /path/to/music/folder --verbose

# Only clean metadata tags, don't rename files
python3 music_renamer.py /path/to/music/folder --metadata-only --dry-run

# Only rename files, don't clean metadata
python3 music_renamer.py /path/to/music/folder --filename-only --verbose

# Combine options
python3 music_renamer.py /path/to/music/folder --dry-run --verbose
```

### Using the Shell Script Wrapper

```bash
# Basic usage
./rename_music.sh /path/to/music/folder

# Dry run mode
./rename_music.sh /path/to/music/folder --dry-run

# Verbose logging
./rename_music.sh /path/to/music/folder --verbose

# Only clean metadata tags
./rename_music.sh /path/to/music/folder --metadata-only --dry-run

# Only rename files
./rename_music.sh /path/to/music/folder --filename-only --verbose

# Show help
./rename_music.sh --help
```

## Examples

### Before and After Examples

| Original Filename | Cleaned Filename |
|-------------------|------------------|
| `01 - Artist - Song Name.mp3` | `Artist - Song Name.mp3` |
| `123_www.example.com_Song Title.flac` | `Song Title.flac` |
| `  05-Artist-Song  .mp3` | `Artist-Song.mp3` |
| `https://site.com/Artist-Song.wav` | `Artist-Song.wav` |
| `001 - 002 - Artist - Song.mp3` | `Artist - Song.mp3` |
| `[2023] Artist - Song.mp3` | `Artist - Song.mp3` |
| `Artist - Song [Remix].mp3` | `Artist - Song.mp3` |
| `Artist   -   Song   Name.mp3` | `Artist - Song Name.mp3` |
| `Artist - Song [].mp3` | `Artist - Song.mp3` |

### Metadata Cleaning Examples

| Original Metadata | Cleaned Metadata |
|-------------------|------------------|
| Title: `[2023] Song Title` | Title: `Song Title` |
| Artist: `www.example.com_Artist Name` | Artist: `Artist Name` |
| Album: `Album   Name   [Remix]` | Album: `Album Name` |
| Title: `01 - 02 - Track Name` | Title: `Track Name` |
| Title: `Song Title []` | Title: `Song Title` |

### Command Examples

```bash
# Preview what would be renamed in your music folder
python3 music_renamer.py ~/Music --dry-run

# Actually rename files in the current directory
python3 music_renamer.py .

# Process a specific folder with verbose logging
python3 music_renamer.py /path/to/playlist --verbose

# Only clean metadata tags (preview mode)
python3 music_renamer.py ~/Music --metadata-only --dry-run

# Only rename files, skip metadata
python3 music_renamer.py ~/Music --filename-only --verbose
```

## Output and Logging

The script provides comprehensive logging:

- **Console Output**: Real-time progress and summary
- **Log File**: Detailed logs saved to `music_renamer.log`
- **Statistics**: Summary of processed, renamed, skipped, and error files

### Sample Output

```
2024-01-15 10:30:15,123 - INFO - Processing directory: /path/to/music
2024-01-15 10:30:15,124 - INFO - Renamed '01 - Artist - Song.mp3' to 'Artist - Song.mp3'
2024-01-15 10:30:15,125 - INFO - Updated metadata for 'Artist - Song.mp3': title: '[2023] Song Title' → 'Song Title'
2024-01-15 10:30:15,126 - INFO - ==================================================
2024-01-15 10:30:15,127 - INFO - PROCESSING STATISTICS
2024-01-15 10:30:15,128 - INFO - ==================================================
2024-01-15 10:30:15,129 - INFO - Total files processed: 150
2024-01-15 10:30:15,130 - INFO - Files renamed: 45
2024-01-15 10:30:15,131 - INFO - Files with metadata updated: 23
2024-01-15 10:30:15,132 - INFO - Files skipped (no changes): 82
2024-01-15 10:30:15,133 - INFO - Errors encountered: 0
```

## Safety Features

- **Dry Run Mode**: Always test with `--dry-run` first to preview changes
- **Backup Recommendation**: Consider backing up your music files before running
- **Conflict Resolution**: Automatically handles filename conflicts
- **Error Recovery**: Continues processing even if individual files fail
- **Detailed Logging**: All operations are logged for audit purposes

## Error Handling

The script handles various error scenarios:

- **File Permission Errors**: Logged and skipped
- **Invalid Filenames**: Cleaned and normalized
- **Duplicate Names**: Automatically resolved with numbering
- **Unicode Issues**: Normalized and cleaned
- **Missing Directories**: Clear error messages

## Requirements

- Python 3.6 or higher
- mutagen library (for metadata editing): `pip install mutagen`

The script will work for filename cleaning without mutagen, but metadata editing requires the mutagen library.

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure you have write permissions to the directory
2. **Python Not Found**: Make sure Python 3 is installed and accessible
3. **Script Not Found**: Ensure you're running from the correct directory

### Getting Help

```bash
# Show Python script help
python3 music_renamer.py --help

# Show shell script help
./rename_music.sh --help
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the script.

## License

This project is open source and available under the MIT License.

## Disclaimer

This script modifies file names. Always test with `--dry-run` first and consider backing up your music files before running the script on important collections. 