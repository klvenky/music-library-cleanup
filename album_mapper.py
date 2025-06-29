#!/usr/bin/env python3
"""
Album Mapper

This script organizes music files from "singles" folders into album folders with the format:
${album name} (${year})

The script:
1. Finds music files in folders named "singles" (case-insensitive)
2. Extracts album name and year from metadata
3. Creates album folders with proper naming
4. Moves files to their respective album folders
5. Handles cases where year is not available

Usage:
    python album_mapper.py [directory_path] [--dry-run] [--verbose] [--create-singles-folder]
"""

import os
import re
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import shutil

try:
    from mutagen import File
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TYER
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.asf import ASF
    from mutagen.mp4 import MP4
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

# Ensure outputs directory exists before configuring logging
os.makedirs('outputs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/album_mapper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Supported music file extensions
MUSIC_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus',
    '.alac', '.aiff', '.dsd', '.dff', '.dsf'
}

class AlbumMapper:
    """Handles the mapping of music files to album folders based on metadata."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False, no_output: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.no_output = no_output
        self.stats = {
            'processed': 0,
            'moved': 0,
            'albums_created': 0,
            'skipped': 0,
            'errors': 0
        }
        # Track created albums
        self.created_albums = []
        
        # Compile regex patterns for better performance
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        
    def is_music_file(self, file_path: Path) -> bool:
        """Check if the file is a music file based on its extension."""
        return file_path.suffix.lower() in MUSIC_EXTENSIONS
    
    def extract_metadata(self, file_path: Path) -> Dict[str, str]:
        """
        Extract album name and year from music file metadata.
        
        Args:
            file_path: Path to the music file
            
        Returns:
            Dictionary with 'album' and 'year' keys
        """
        if not MUTAGEN_AVAILABLE:
            return {'album': 'Unknown Album', 'year': ''}
        
        try:
            audio = File(str(file_path))
            if audio is None:
                return {'album': 'Unknown Album', 'year': ''}
            
            album_name = 'Unknown Album'
            year = ''
            
            # Handle different audio formats
            if hasattr(audio, 'tags') and audio.tags:
                if hasattr(audio.tags, 'getall'):  # ID3 tags (MP3)
                    album_name, year = self._extract_id3_metadata(audio.tags)
                elif hasattr(audio.tags, 'get'):  # Vorbis comments (FLAC, OGG)
                    album_name, year = self._extract_vorbis_metadata(audio.tags)
                elif hasattr(audio.tags, 'getAttribute'):  # ASF tags (WMA)
                    album_name, year = self._extract_asf_metadata(audio.tags)
                elif hasattr(audio.tags, 'get'):  # MP4 tags (M4A)
                    album_name, year = self._extract_mp4_metadata(audio.tags)
            
            return {'album': album_name, 'year': year}
            
        except Exception as e:
            logger.warning(f"Error extracting metadata from {file_path}: {str(e)}")
            return {'album': 'Unknown Album', 'year': ''}
    
    def _extract_id3_metadata(self, tags) -> Tuple[str, str]:
        """Extract album and year from ID3 tags (MP3 files)."""
        album_name = 'Unknown Album'
        year = ''
        
        if 'TALB' in tags:
            album_name = str(tags['TALB'])
        
        # Try different year fields
        if 'TDRC' in tags:
            year = str(tags['TDRC'])
        elif 'TYER' in tags:
            year = str(tags['TYER'])
        
        return album_name, year
    
    def _extract_vorbis_metadata(self, tags) -> Tuple[str, str]:
        """Extract album and year from Vorbis comments (FLAC, OGG files)."""
        album_name = 'Unknown Album'
        year = ''
        
        if 'album' in tags:
            album_name = tags['album'][0]
        
        if 'date' in tags:
            year = tags['date'][0]
        elif 'year' in tags:
            year = tags['year'][0]
        
        return album_name, year
    
    def _extract_asf_metadata(self, tags) -> Tuple[str, str]:
        """Extract album and year from ASF tags (WMA files)."""
        album_name = 'Unknown Album'
        year = ''
        
        if tags.getAttribute('WM/AlbumTitle'):
            album_name = tags.getAttribute('WM/AlbumTitle')[0]
        
        if tags.getAttribute('WM/Year'):
            year = tags.getAttribute('WM/Year')[0]
        
        return album_name, year
    
    def _extract_mp4_metadata(self, tags) -> Tuple[str, str]:
        """Extract album and year from MP4 tags (M4A files)."""
        album_name = 'Unknown Album'
        year = ''
        
        if '\xa9alb' in tags:
            album_name = tags['\xa9alb'][0]
        
        if '\xa9day' in tags:
            year = tags['\xa9day'][0]
        
        return album_name, year
    
    def clean_album_name(self, album_name: str) -> str:
        """
        Clean album name by removing invalid characters and normalizing.
        
        Args:
            album_name: Original album name
            
        Returns:
            Cleaned album name
        """
        if not album_name or album_name == 'Unknown Album':
            return 'Unknown Album'
        
        # Remove invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            album_name = album_name.replace(char, '')
        
        # Normalize spaces
        album_name = ' '.join(album_name.split())
        
        # Remove leading/trailing spaces
        album_name = album_name.strip()
        
        return album_name if album_name else 'Unknown Album'
    
    def extract_year(self, year_string: str) -> str:
        """
        Extract year from various year formats.
        
        Args:
            year_string: Year string from metadata
            
        Returns:
            Extracted year or empty string
        """
        if not year_string:
            return ''
        
        # Look for 4-digit year pattern
        match = self.year_pattern.search(str(year_string))
        if match:
            return match.group()
        
        return ''
    
    def create_album_folder_name(self, album_name: str, year: str) -> str:
        """
        Create album folder name with proper format.
        Avoids duplicating year if it's already present in the album name.
        
        Args:
            album_name: Cleaned album name
            year: Extracted year
            
        Returns:
            Album folder name
        """
        if not year:
            return album_name
        
        # Check if the year is already present in the album name
        # Look for year patterns like (2023), [2023], 2023, etc.
        year_patterns = [
            rf'\({year}\)',  # (2023)
            rf'\[{year}\]',  # [2023]
            rf'\b{year}\b',  # 2023 (word boundary)
        ]
        
        for pattern in year_patterns:
            if re.search(pattern, album_name, re.IGNORECASE):
                # Year is already in the album name, don't add it again
                return album_name
        
        # Year is not in the album name, add it
        return f"{album_name} ({year})"
    
    def process_file(self, file_path: Path, source_directory: Path) -> Tuple[bool, str]:
        """
        Process a single music file for album mapping.
        
        Args:
            file_path: Path to the music file
            source_directory: Path to the source directory containing the file
            
        Returns:
            Tuple of (success, result_message)
        """
        try:
            if not self.is_music_file(file_path):
                return False, "Not a music file"
            
            # Extract metadata
            metadata = self.extract_metadata(file_path)
            album_name = self.clean_album_name(metadata['album'])
            year = self.extract_year(metadata['year'])
            
            # Create album folder name
            album_folder_name = self.create_album_folder_name(album_name, year)
            
            # Create album folder path
            album_folder = source_directory.parent / album_folder_name
            
            # Create album folder if it doesn't exist
            if not album_folder.exists():
                if self.dry_run:
                    logger.info(f"DRY RUN: Would create album folder: {album_folder}")
                    self.created_albums.append(str(album_folder))
                else:
                    album_folder.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created album folder: {album_folder}")
                    self.stats['albums_created'] += 1
                    self.created_albums.append(str(album_folder))
            
            # Create destination file path
            dest_file = album_folder / file_path.name
            
            # Handle filename conflicts
            if dest_file.exists() and dest_file != file_path:
                counter = 1
                name_without_ext, ext = os.path.splitext(file_path.name)
                while dest_file.exists():
                    new_name = f"{name_without_ext} ({counter}){ext}"
                    dest_file = album_folder / new_name
                    counter += 1
            
            # Move the file
            if self.dry_run:
                logger.info(f"DRY RUN: Would move '{file_path.name}' to '{album_folder_name}/'")
            else:
                shutil.move(str(file_path), str(dest_file))
                logger.info(f"Moved '{file_path.name}' to '{album_folder_name}/'")
            
            return True, f"Moved to {album_folder_name}/"
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def process_music_directory(self, music_directory: Path) -> None:
        """
        Process all music files in a directory.
        Only moves files to album folders if the album contains more than 3 songs.
        
        Args:
            music_directory: Path to the directory containing music files
        """
        logger.info(f"Processing music directory: {music_directory}")
        
        # Get all music files in the directory
        music_files = [f for f in music_directory.iterdir() if f.is_file() and self.is_music_file(f)]
        
        if not music_files:
            logger.info(f"No music files found in {music_directory}")
            return
        
        # Group files by album
        album_groups = {}
        for file_path in music_files:
            metadata = self.extract_metadata(file_path)
            album_name = self.clean_album_name(metadata['album'])
            year = self.extract_year(metadata['year'])
            album_key = self.create_album_folder_name(album_name, year)
            
            if album_key not in album_groups:
                album_groups[album_key] = []
            album_groups[album_key].append(file_path)
        
        # Process each album group
        for album_key, files in album_groups.items():
            if len(files) <= 3:
                # Album with 3 or fewer songs - leave in current directory
                for file_path in files:
                    self.stats['processed'] += 1
                    self.stats['skipped'] += 1
                    if self.verbose:
                        logger.debug(f"Skipped album (<=3 songs): {file_path.name} (album: {album_key})")
                    logger.info(f"Album '{album_key}' has {len(files)} song(s) - leaving in current directory")
            else:
                # Album with more than 3 songs - move them to album folder
                logger.info(f"Album '{album_key}' with {len(files)} songs - moving to album folder")
                for file_path in files:
                    self.stats['processed'] += 1
                    
                    success, result = self.process_file(file_path, music_directory)
                    
                    if success:
                        self.stats['moved'] += 1
                    else:
                        self.stats['errors'] += 1
                    
                    if self.verbose:
                        logger.debug(f"Processed: {file_path} - {result}")
    
    def process_directory(self, directory_path: Path) -> None:
        """
        Recursively process all music files in the directory and organize them into album folders.
        
        Args:
            directory_path: Path to the directory to process
        """
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory_path}")
            return
        
        if not directory_path.is_dir():
            logger.error(f"Path is not a directory: {directory_path}")
            return
        
        logger.info(f"Processing directory: {directory_path}")
        
        # Process the current directory
        self.process_music_directory(directory_path)
        
        # Optionally process subdirectories recursively
        # Note: This could be made configurable with a --recursive flag
        for item in directory_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):  # Skip hidden directories
                self.process_music_directory(item)
    
    def write_outputs_report(self):
        """Write a markdown report of created albums to outputs folder."""
        if self.no_output:
            return
            
        if not self.created_albums:
            return
        from datetime import datetime
        from pathlib import Path
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = outputs_dir / f"album_mapper_{timestamp}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Album Mapper Report - {timestamp}\n\n")
            f.write("Generated by album_mapper.py\n\n")
            f.write(f"## Albums Created ({len(self.created_albums)})\n\n")
            f.write("| Album Folder |\n")
            f.write("|--------------|\n")
            for album in self.created_albums:
                f.write(f"| `{album}` |\n")
            f.write("\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total Files Processed**: {self.stats['processed']}\n")
            f.write(f"- **Albums Created**: {len(self.created_albums)}\n")
            f.write(f"- **Files Processed**: {self.stats['processed']}\n")
            f.write(f"- **Files Moved**: {self.stats['moved']}\n")
            f.write(f"- **Files Skipped**: {self.stats['skipped']}\n")
            f.write(f"- **Errors**: {self.stats['errors']}\n")
            if self.dry_run:
                f.write("\n> **Note**: This was a dry run - no files or folders were actually modified.\n")
        logger.info(f"Album report written to: {filename}")
        
        # Remove previous album_mapper_*.md files
        for old_file in outputs_dir.glob('album_mapper_*.md'):
            try:
                old_file.unlink()
            except Exception:
                pass
    
    def print_stats(self) -> None:
        """Print processing statistics."""
        logger.info("=" * 50)
        logger.info("ALBUM MAPPING STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total files processed: {self.stats['processed']}")
        logger.info(f"Files moved: {self.stats['moved']}")
        logger.info(f"Albums created: {self.stats['albums_created']}")
        logger.info(f"Files skipped: {self.stats['skipped']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        
        if self.dry_run:
            logger.info("DRY RUN MODE - No files were actually moved or folders created")
        # Write outputs report
        self.write_outputs_report()

    def get_created_albums(self):
        """Return the list of created album folder names."""
        return self.created_albums

def main():
    """Main function to handle command line arguments and execute the album mapping process."""
    parser = argparse.ArgumentParser(
        description="Organize music files into album folders based on metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python album_mapper.py /path/to/music/folder
  python album_mapper.py . --dry-run --verbose
  python album_mapper.py /music --dry-run
        """
    )
    
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Directory containing music files to process (default: current directory)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be moved without actually moving files'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--no-output',
        action='store_true',
        help='Prevent generating output files during tests'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if mutagen is available for metadata operations
    if not MUTAGEN_AVAILABLE:
        logger.warning("Mutagen library not available. Install with: pip install mutagen")
        logger.warning("Album mapping will use 'Unknown Album' for files without metadata")
    
    # Create and run the mapper
    mapper = AlbumMapper(
        dry_run=args.dry_run, 
        verbose=args.verbose,
        no_output=args.no_output
    )
    
    try:
        directory_path = Path(args.directory).resolve()
        mapper.process_directory(directory_path)
        mapper.print_stats()
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 