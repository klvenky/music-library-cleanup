#!/usr/bin/env python3
"""
Music File Renamer

This script recursively processes music files in a directory and cleans up their names by:
1. Removing leading numbers, dashes, underscores, dots, spaces, and square brackets
2. Removing website details (URLs, domain names)
3. Removing trailing square brackets and their content
4. Removing any remaining empty brackets
5. Normalizing multiple spaces and whitespace characters throughout the filename
6. Normalizing unicode characters and removing invalid filename characters

The script runs recursively until no more patterns are found to replace, ensuring complete cleaning.
The script also cleans up music metadata (ID3 tags) with the same rules.

Usage:
    python music_renamer.py [directory_path] [--dry-run] [--verbose] [--metadata-only] [--filename-only]
"""

import os
import re
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import unicodedata
from datetime import datetime

try:
    from mutagen import File
    from mutagen.id3 import ID3, TIT2, TPE1, TALB
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
        logging.FileHandler('outputs/music_renamer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Supported music file extensions
MUSIC_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus',
    '.alac', '.aiff', '.dsd', '.dff', '.dsf'
}

class MusicRenamer:
    """Handles the renaming of music files with various cleanup operations."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False, metadata_only: bool = False, filename_only: bool = False, debug: bool = False, no_output: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.metadata_only = metadata_only
        self.filename_only = filename_only
        self.debug = debug
        self.no_output = no_output
        self.stats = {
            'processed': 0,
            'renamed': 0,
            'metadata_updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Track unique URLs that are replaced
        self.replaced_urls = set()
        
        # Track original and final filenames for markdown table
        self.filename_changes = []
        
        # Track error details for reporting
        self.error_details = []
        
        # Compile regex patterns for better performance
        self.leading_numbers_pattern = re.compile(r'^[\d\s\-_\.]+|^\[[^\]]*\][\s\-_\.]*')
        # Match only the domain if preceded by a separator or start, and followed by a separator, dot, or end
        self.website_pattern = re.compile(r'(?:www\.|https?://)?[a-zA-Z0-9\-]+\.(?:com|co|in|net|ws|io)', re.IGNORECASE)
        self.trailing_separator_pattern = re.compile(r'[-_\s]+$')
        self.bitrate_pattern = re.compile(r'[-_\s]*(?:320|256|192|160|128|96|64)[-_\s]*k\s*b\s*p\s*s?[-_\s]*', re.IGNORECASE)
        self.repeated_extension_pattern = re.compile(r'\.(mp3|flac|wav|aac|ogg|m4a|wma|opus|alac|aiff|dsd|dff|dsf)\.(mp3|flac|wav|aac|ogg|m4a|wma|opus|alac|aiff|dsd|dff|dsf)$', re.IGNORECASE)
        self.multiple_spaces_pattern = re.compile(r'\s')
        self.trailing_spaces_pattern = re.compile(r'\s+$')
        self.trailing_brackets_pattern = re.compile(r'[\s\-_\.]*\[[^\]]*\]$')
        self.leading_spaces_pattern = re.compile(r'^\s+')
        self.empty_brackets_pattern = re.compile(r'\[\s*\]')
        
    def is_music_file(self, file_path: Path) -> bool:
        """Check if the file is a music file based on its extension."""
        return file_path.suffix.lower() in MUSIC_EXTENSIONS
    
    def clean_filename(self, filename: str) -> str:
        """
        Clean the filename by applying various transformations, but preserve [w+].ft and ft.[w+] patterns.
        """
        # Step 0: Remove repeated file extensions (e.g., .mp3.mp3 -> .mp3)
        filename = self.repeated_extension_pattern.sub(r'.\1', filename)
        name, ext = os.path.splitext(filename)

        # Preserve [w+].ft and ft.[w+] patterns
        preserved = []
        def preserve_ft(match):
            preserved.append(match.group(0))
            return f"__FTPRESERVE{len(preserved)-1}__"
        # Regex for [w+].ft or ft.[w+]
        ft_pattern = re.compile(r'(\[[^\]]+\]\.ft|ft\.\[[^\]]+\])', re.IGNORECASE)
        name = ft_pattern.sub(preserve_ft, name)

        # Step 1: Remove leading numbers, dashes, underscores, dots, spaces, and square brackets
        name = self.leading_numbers_pattern.sub('', name)
        # Step 2: Remove website details (URLs, domain names) and track them
        original_name = name
        parts = re.split(r'([\-_ ])', name)
        filtered_parts = []
        for part in parts:
            if self.website_pattern.fullmatch(part):
                cleaned_url = part.strip('-_ ')
                if cleaned_url:
                    self.replaced_urls.add(cleaned_url)
                continue
            filtered_parts.append(part)
        name = ''.join(filtered_parts)
        name = self.trailing_separator_pattern.sub('', name)
        # Step 3: Remove bitrate information
        name = self.bitrate_pattern.sub('', name)
        # Step 4: Remove trailing square brackets and their content
        name = self.trailing_brackets_pattern.sub('', name)
        # Step 5: Remove any remaining empty brackets
        name = self.empty_brackets_pattern.sub('', name)
        # Step 6: Normalize all whitespace characters to single spaces
        name = self.multiple_spaces_pattern.sub(' ', name)
        # Step 7: Remove leading and trailing spaces
        name = name.strip()
        # Step 8: Normalize unicode characters
        name = unicodedata.normalize('NFKC', name)
        # Step 9: Replace invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '')
        # FINAL: Remove leading numbers, dashes, underscores, dots, spaces, and square brackets again
        name = self.leading_numbers_pattern.sub('', name)
        # Restore preserved ft patterns
        def restore_ft(m):
            idx = int(m.group(1))
            return preserved[idx]
        name = re.sub(r'__FTPRESERVE(\d+)__', restore_ft, name)
        if not name:
            name = "Unknown Track"
        return name + ext
    
    def process_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Process a single music file for renaming and metadata cleaning.
        
        Args:
            file_path: Path to the music file
            
        Returns:
            Tuple of (success, new_name or error_message)
        """
        try:
            if not self.is_music_file(file_path):
                return False, "Not a music file"
            
            original_name = file_path.name
            filename_changed = False
            metadata_changed = False
            results = []
            
            # Handle filename cleaning
            if not self.metadata_only:
                cleaned_name = self.clean_filename(original_name)
                if cleaned_name != original_name:
                    new_path = file_path.parent / cleaned_name
                    
                    # Check if the new filename already exists
                    if new_path.exists() and new_path != file_path:
                        counter = 1
                        while new_path.exists():
                            name_without_ext, ext = os.path.splitext(cleaned_name)
                            new_name = f"{name_without_ext} ({counter}){ext}"
                            new_path = file_path.parent / new_name
                            counter += 1
                    
                    # Track the filename change for markdown table
                    self.filename_changes.append({
                        'original': original_name,
                        'final': new_path.name,
                        'path': str(file_path.parent)
                    })
                    
                    if self.dry_run:
                        logger.info(f"DRY RUN: Would rename '{original_name}' to '{new_path.name}'")
                    else:
                        file_path.rename(new_path)
                        logger.info(f"Renamed '{original_name}' to '{new_path.name}'")
                        file_path = new_path  # Update file_path for metadata processing
                    
                    filename_changed = True
                    results.append(f"filename: '{original_name}' → '{new_path.name}'")
            
            # Handle metadata cleaning
            if not self.filename_only:
                metadata_success, metadata_result = self.clean_metadata(file_path)
                if metadata_success and "Metadata updated" in metadata_result:
                    metadata_changed = True
                    results.append(metadata_result)
                elif not metadata_success:
                    results.append(f"metadata error: {metadata_result}")
            
            if filename_changed or metadata_changed:
                return True, "; ".join(results)
            else:
                return True, "No changes needed"
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            logger.error(error_msg)
            # Track error details for reporting
            self.error_details.append({
                'filename': file_path.name,
                'path': str(file_path.parent),
                'error': str(e)
            })
            return False, error_msg
    
    def process_directory(self, directory_path: Path) -> None:
        """
        Recursively process all music files in the directory until no more changes are needed.
        
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
        
        # Track total changes across all passes
        total_passes = 0
        total_changes = 0
        
        # For dry-run mode, track virtual file states
        virtual_files = {}
        
        while True:
            pass_number = total_passes + 1
            logger.info(f"Starting pass {pass_number}...")
            
            # Reset stats for this pass
            pass_stats = {
                'processed': 0,
                'renamed': 0,
                'metadata_updated': 0,
                'errors': 0,
                'skipped': 0
            }
            
            changes_in_pass = 0
            
            # Walk through all files recursively
            for root, dirs, files in os.walk(directory_path):
                root_path = Path(root)
                
                for file_name in files:
                    file_path = root_path / file_name
                    pass_stats['processed'] += 1
                    
                    # In dry-run mode, use virtual file path if it exists
                    if self.dry_run and str(file_path) in virtual_files:
                        virtual_name = virtual_files[str(file_path)]
                        # Create a virtual file path for processing
                        virtual_path = file_path.parent / virtual_name
                        success, result = self.process_file(virtual_path)
                    else:
                        success, result = self.process_file(file_path)
                    
                    if success:
                        if result != "No changes needed":
                            if "filename:" in result:
                                pass_stats['renamed'] += 1
                                changes_in_pass += 1
                                
                                # In dry-run mode, update virtual file state
                                if self.dry_run:
                                    # Extract the new name from the result
                                    import re
                                    match = re.search(r"filename: '.*?' → '(.+?)'", result)
                                    if match:
                                        new_name = match.group(1)
                                        virtual_files[str(file_path)] = new_name
                            if "Metadata updated" in result:
                                pass_stats['metadata_updated'] += 1
                                changes_in_pass += 1
                        else:
                            pass_stats['skipped'] += 1
                    else:
                        pass_stats['errors'] += 1
                    
                    if self.debug:
                        logger.debug(f"Processed: {file_path} - {result}")
            
            # Update total stats
            self.stats['processed'] += pass_stats['processed']
            self.stats['renamed'] += pass_stats['renamed']
            self.stats['metadata_updated'] += pass_stats['metadata_updated']
            self.stats['errors'] += pass_stats['errors']
            self.stats['skipped'] += pass_stats['skipped']
            
            total_changes += changes_in_pass
            total_passes += 1
            
            # Log pass results
            if changes_in_pass > 0:
                logger.info(f"Pass {pass_number} completed: {changes_in_pass} changes made")
                if self.verbose:
                    logger.info(f"  - Files renamed: {pass_stats['renamed']}")
                    logger.info(f"  - Metadata updated: {pass_stats['metadata_updated']}")
                    logger.info(f"  - Files skipped: {pass_stats['skipped']}")
                    logger.info(f"  - Errors: {pass_stats['errors']}")
            else:
                logger.info(f"Pass {pass_number} completed: No changes needed")
                break
            
            # Safety check to prevent infinite loops
            if total_passes > 10:
                logger.warning(f"Reached maximum number of passes ({total_passes}). Stopping to prevent infinite loop.")
                break
        
        logger.info(f"Processing completed after {total_passes} passes with {total_changes} total changes")
    
    def print_stats(self) -> None:
        """Print processing statistics."""
        logger.info("=" * 50)
        logger.info("PROCESSING STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total files processed: {self.stats['processed']}")
        logger.info(f"Files renamed: {self.stats['renamed']}")
        logger.info(f"Files with metadata updated: {self.stats['metadata_updated']}")
        logger.info(f"Files skipped (no changes): {self.stats['skipped']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        
        # Display unique URLs that were replaced
        if self.replaced_urls:
            logger.info("=" * 50)
            logger.info("UNIQUE URLS REPLACED")
            logger.info("=" * 50)
            for url in sorted(self.replaced_urls):
                logger.info(f"  - {url}")
            logger.info(f"Total unique URLs replaced: {len(self.replaced_urls)}")
            
            # Write URLs to file
            self.write_urls_to_file()
        
        if self.dry_run:
            logger.info("DRY RUN MODE - No files were actually renamed or modified")
        
        logger.info("=" * 50)
    
    def write_urls_to_file(self, album_results=None) -> None:
        """Write the unique URLs, filename changes, and optionally album results to a markdown file with collapsible sections."""
        if self.no_output:
            return
            
        if not self.replaced_urls and not self.filename_changes and not album_results and not self.error_details:
            return
            
        try:
            # Create outputs directory if it doesn't exist
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)
            
            # Remove previous replaced_urls_*.md files
            for old_file in outputs_dir.glob('replaced_urls.md'):
                try:
                    old_file.unlink()
                except Exception:
                    pass
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = outputs_dir / f"replaced_urls.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Music File Processing Report - {timestamp}\n\n")
                f.write("Generated by music_renamer.py\n\n")
                
                # Albums Created Section
                if album_results:
                    f.write("## Albums Created\n\n")
                    f.write(f"Total albums created: **{len(album_results)}**\n\n")
                    f.write("| Album Folder |\n")
                    f.write("|--------------|\n")
                    for album in album_results:
                        f.write(f"| `{album}` |\n")
                    f.write("\n")
                
                # Filename Changes Section
                if self.filename_changes:
                    f.write("## Filename Changes\n\n")
                    f.write(f"Total files renamed: **{len(self.filename_changes)}**\n\n")
                    f.write("| Original Filename | Final Filename | Directory |\n")
                    f.write("|-------------------|----------------|-----------|\n")
                    for change in self.filename_changes:
                        # Escape pipe characters in filenames for markdown table
                        original = change['original'].replace('|', '\\|')
                        final = change['final'].replace('|', '\\|')
                        path = change['path'].replace('|', '\\|')
                        f.write(f"| `{original}` | `{final}` | `{path}` |\n")
                    f.write("\n")
                
                # URLs Section
                if self.replaced_urls:
                    f.write("## URLs Replaced\n\n")
                    f.write(f"Total unique URLs replaced: **{len(self.replaced_urls)}**\n\n")
                    f.write("| URL |\n")
                    f.write("|-----|\n")
                    for url in sorted(self.replaced_urls):
                        f.write(f"| {url} |\n")
                    f.write("\n")
                
                # Error Details Section
                if self.error_details:
                    f.write("## Error Details\n\n")
                    f.write(f"Total errors encountered: **{len(self.error_details)}**\n\n")
                    f.write("| Filename | Error |\n")
                    f.write("|----------|-------|\n")
                    for error in self.error_details:
                        # Escape pipe characters for markdown table
                        filename = error['filename'].replace('|', '\\|')
                        error_msg = error['error'].replace('|', '\\|')
                        f.write(f"| `{filename}` | {error_msg} |\n")
                    f.write("\n")
                
                # Write summary
                f.write("## Summary\n\n")
                f.write(f"- **Total Files Processed**: {self.stats['processed']}\n")
                f.write(f"- **Processing Date**: {timestamp}\n")
                f.write(f"- **Files Renamed**: {self.stats['renamed']}\n")
                f.write(f"- **Metadata Updated**: {self.stats['metadata_updated']}\n")
                f.write(f"- **Files Skipped**: {self.stats['skipped']}\n")
                f.write(f"- **Errors**: {self.stats['errors']}\n")
                if self.replaced_urls:
                    f.write(f"- **Unique URLs Replaced**: {len(self.replaced_urls)}\n")
                if album_results:
                    f.write(f"- **Albums Created**: {len(album_results)}\n")
                if self.dry_run:
                    f.write("\n> **Note**: This was a dry run - no files were actually modified.\n")
            
            logger.info(f"Report written to: {filename}")
            
        except Exception as e:
            logger.error(f"Error writing report to file: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean text using the same rules as filename cleaning, but preserve [w+].ft and ft.[w+] patterns.
        """
        if not text:
            return text
        preserved = []
        def preserve_ft(match):
            preserved.append(match.group(0))
            return f"__FTPRESERVE{len(preserved)-1}__"
        ft_pattern = re.compile(r'(\[[^\]]+\]\.ft|ft\.\[[^\]]+\])', re.IGNORECASE)
        text = ft_pattern.sub(preserve_ft, text)
        text = self.leading_numbers_pattern.sub('', text)
        original_text = text
        text = self.website_pattern.sub('', text)
        if text != original_text:
            matches = self.website_pattern.findall(original_text)
            for match in matches:
                cleaned_url = match.strip('-_ ')
                if cleaned_url:
                    self.replaced_urls.add(cleaned_url)
        text = self.bitrate_pattern.sub('', text)
        text = self.trailing_brackets_pattern.sub('', text)
        text = self.empty_brackets_pattern.sub('', text)
        text = self.multiple_spaces_pattern.sub(' ', text)
        text = text.strip()
        text = unicodedata.normalize('NFKC', text)
        def restore_ft(m):
            idx = int(m.group(1))
            return preserved[idx]
        text = re.sub(r'__FTPRESERVE(\d+)__', restore_ft, text)
        return text
    
    def clean_metadata(self, file_path: Path) -> Tuple[bool, str]:
        """
        Clean metadata tags for a music file.
        
        Args:
            file_path: Path to the music file
            
        Returns:
            Tuple of (success, result_message)
        """
        if not MUTAGEN_AVAILABLE:
            return False, "Mutagen library not available for metadata editing"
        
        try:
            # Try to load the file with mutagen
            audio = File(str(file_path))
            if audio is None:
                return False, "Could not read metadata"
            
            changes_made = False
            changes_log = []
            
            # Handle different audio formats
            if hasattr(audio, 'tags') and audio.tags:
                if hasattr(audio.tags, 'getall'):  # ID3 tags (MP3)
                    changes_made, changes_log = self._clean_id3_tags(audio.tags, changes_log)
                elif hasattr(audio.tags, 'get'):  # Vorbis comments (FLAC, OGG)
                    changes_made, changes_log = self._clean_vorbis_tags(audio.tags, changes_log)
                elif hasattr(audio.tags, 'getAttribute'):  # ASF tags (WMA)
                    changes_made, changes_log = self._clean_asf_tags(audio.tags, changes_log)
                elif hasattr(audio.tags, 'get'):  # MP4 tags (M4A)
                    changes_made, changes_log = self._clean_mp4_tags(audio.tags, changes_log)
            
            if changes_made:
                if not self.dry_run:
                    audio.save()
                    logger.info(f"Updated metadata for {file_path.name}: {', '.join(changes_log)}")
                else:
                    logger.info(f"DRY RUN: Would update metadata for {file_path.name}: {', '.join(changes_log)}")
                
                return True, f"Metadata updated: {', '.join(changes_log)}"
            else:
                return True, "No metadata changes needed"
                
        except Exception as e:
            error_msg = f"Error processing metadata for {file_path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _clean_id3_tags(self, tags, changes_log: List[str]) -> Tuple[bool, List[str]]:
        """Clean ID3 tags (MP3 files)."""
        changes_made = False
        # Clean title
        if 'TIT2' in tags:
            original_title = str(tags['TIT2'])
            cleaned_title = self.clean_text(original_title)
            if cleaned_title != original_title:
                if not self.dry_run:
                    tags['TIT2'] = TIT2(encoding=3, text=cleaned_title)
                changes_log.append(f"title: '{original_title}' → '{cleaned_title}'")
                changes_made = True
        # Clean artist
        if 'TPE1' in tags:
            original_artist = str(tags['TPE1'])
            cleaned_artist = self.clean_text(original_artist)
            if cleaned_artist != original_artist:
                if not self.dry_run:
                    tags['TPE1'] = TPE1(encoding=3, text=cleaned_artist)
                changes_log.append(f"artist: '{original_artist}' → '{cleaned_artist}'")
                changes_made = True
        # Clean album
        if 'TALB' in tags:
            original_album = str(tags['TALB'])
            cleaned_album = self.clean_text(original_album)
            if cleaned_album != original_album:
                if not self.dry_run:
                    tags['TALB'] = TALB(encoding=3, text=cleaned_album)
                changes_log.append(f"album: '{original_album}' → '{cleaned_album}'")
                changes_made = True
        # Do NOT clean composer or other fields
        return changes_made, changes_log
    
    def _clean_vorbis_tags(self, tags, changes_log: List[str]) -> Tuple[bool, List[str]]:
        """Clean Vorbis comments (FLAC, OGG files)."""
        changes_made = False
        # Clean title
        if 'title' in tags:
            original_title = tags['title'][0]
            cleaned_title = self.clean_text(original_title)
            if cleaned_title != original_title:
                if not self.dry_run:
                    tags['title'] = [cleaned_title]
                changes_log.append(f"title: '{original_title}' → '{cleaned_title}'")
                changes_made = True
        # Clean artist
        if 'artist' in tags:
            original_artist = tags['artist'][0]
            cleaned_artist = self.clean_text(original_artist)
            if cleaned_artist != original_artist:
                if not self.dry_run:
                    tags['artist'] = [cleaned_artist]
                changes_log.append(f"artist: '{original_artist}' → '{cleaned_artist}'")
                changes_made = True
        # Clean album
        if 'album' in tags:
            original_album = tags['album'][0]
            cleaned_album = self.clean_text(original_album)
            if cleaned_album != original_album:
                if not self.dry_run:
                    tags['album'] = [cleaned_album]
                changes_log.append(f"album: '{original_album}' → '{cleaned_album}'")
                changes_made = True
        # Do NOT clean composer or other fields
        return changes_made, changes_log
    
    def _clean_asf_tags(self, tags, changes_log: List[str]) -> Tuple[bool, List[str]]:
        """Clean ASF tags (WMA files)."""
        changes_made = False
        # Clean title
        if tags.getAttribute('Title'):
            original_title = tags.getAttribute('Title')[0]
            cleaned_title = self.clean_text(original_title)
            if cleaned_title != original_title:
                if not self.dry_run:
                    tags.setAttribute('Title', [cleaned_title])
                changes_log.append(f"title: '{original_title}' → '{cleaned_title}'")
                changes_made = True
        # Clean artist
        if tags.getAttribute('Author'):
            original_artist = tags.getAttribute('Author')[0]
            cleaned_artist = self.clean_text(original_artist)
            if cleaned_artist != original_artist:
                if not self.dry_run:
                    tags.setAttribute('Author', [cleaned_artist])
                changes_log.append(f"artist: '{original_artist}' → '{cleaned_artist}'")
                changes_made = True
        # Clean album
        if tags.getAttribute('WM/AlbumTitle'):
            original_album = tags.getAttribute('WM/AlbumTitle')[0]
            cleaned_album = self.clean_text(original_album)
            if cleaned_album != original_album:
                if not self.dry_run:
                    tags.setAttribute('WM/AlbumTitle', [cleaned_album])
                changes_log.append(f"album: '{original_album}' → '{cleaned_album}'")
                changes_made = True
        # Do NOT clean composer or other fields
        return changes_made, changes_log
    
    def _clean_mp4_tags(self, tags, changes_log: List[str]) -> Tuple[bool, List[str]]:
        """Clean MP4 tags (M4A files)."""
        changes_made = False
        # Clean title
        if '\xa9nam' in tags:
            original_title = tags['\xa9nam'][0]
            cleaned_title = self.clean_text(original_title)
            if cleaned_title != original_title:
                if not self.dry_run:
                    tags['\xa9nam'] = [cleaned_title]
                changes_log.append(f"title: '{original_title}' → '{cleaned_title}'")
                changes_made = True
        # Clean artist
        if '\xa9ART' in tags:
            original_artist = tags['\xa9ART'][0]
            cleaned_artist = self.clean_text(original_artist)
            if cleaned_artist != original_artist:
                if not self.dry_run:
                    tags['\xa9ART'] = [cleaned_artist]
                changes_log.append(f"artist: '{original_artist}' → '{cleaned_artist}'")
                changes_made = True
        # Clean album
        if '\xa9alb' in tags:
            original_album = tags['\xa9alb'][0]
            cleaned_album = self.clean_text(original_album)
            if cleaned_album != original_album:
                if not self.dry_run:
                    tags['\xa9alb'] = [cleaned_album]
                changes_log.append(f"album: '{original_album}' → '{cleaned_album}'")
                changes_made = True
        # Do NOT clean composer or other fields
        return changes_made, changes_log

def main():
    """Main function to handle command line arguments and execute the renaming process."""
    parser = argparse.ArgumentParser(
        description="Clean up music file names and metadata by removing leading numbers, website details, and trailing spaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python music_renamer.py /path/to/music/folder
  python music_renamer.py . --dry-run --verbose
  python music_renamer.py /music --dry-run
  python music_renamer.py /music --metadata-only --dry-run
  python music_renamer.py /music --filename-only --verbose
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
        help='Show what would be renamed/modified without actually making changes'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--metadata-only',
        action='store_true',
        help='Only clean metadata tags, do not rename files'
    )
    
    parser.add_argument(
        '--filename-only',
        action='store_true',
        help='Only rename files, do not clean metadata tags'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging (shows debug logs)'
    )
    
    parser.add_argument(
        '--no-output',
        action='store_true',
        help='Prevent generating output files during tests'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.metadata_only and args.filename_only:
        logger.error("Cannot use both --metadata-only and --filename-only")
        return 1
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Check if mutagen is available for metadata operations
    if not args.filename_only and not MUTAGEN_AVAILABLE:
        logger.warning("Mutagen library not available. Install with: pip install mutagen")
        logger.warning("Metadata cleaning will be skipped. Use --filename-only to continue with filename cleaning only.")
        if not args.metadata_only:
            logger.info("Continuing with filename cleaning only...")
            args.filename_only = True
        else:
            logger.error("Cannot perform metadata-only operations without mutagen library")
            return 1
    
    # Create and run the renamer
    renamer = MusicRenamer(
        dry_run=args.dry_run, 
        verbose=args.verbose, 
        metadata_only=args.metadata_only, 
        filename_only=args.filename_only,
        debug=args.debug,
        no_output=args.no_output
    )
    
    try:
        directory_path = Path(args.directory).resolve()
        renamer.process_directory(directory_path)
        renamer.print_stats()
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 