#!/usr/bin/env python3
"""
Music Metadata Fixer

A powerful Python script to clean up music file names and metadata by removing
leading numbers, website details, trailing spaces, and organizing files into albums.

Features:
- Recursive multi-pass filename cleaning
- Metadata tag cleaning (ID3, Vorbis, ASF, MP4)
- Album organization
- URL tracking and reporting
- Dry-run mode for previewing changes
- Comprehensive logging and error handling

Usage:
    python music_metadata_fixer.py [directory_path] [--dry-run] [--verbose] [--metadata-only] [--filename-only]

Examples:
    python music_metadata_fixer.py /path/to/music/folder
    python music_metadata_fixer.py . --dry-run --verbose
    python music_metadata_fixer.py /music --dry-run
    python music_metadata_fixer.py /music --metadata-only --dry-run
    python music_metadata_fixer.py /music --filename-only --verbose

Author: Generated with Cursor
License: MIT
"""

import os
import re
import sys
import argparse
import logging
import unicodedata
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Set
from collections import defaultdict

# Try to import mutagen for metadata handling
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
    File = None
    ID3 = None
    TIT2 = None
    TPE1 = None
    TALB = None

# Check for DEBUG environment variable
DEBUG_MODE = os.getenv('DEBUG', 'false').lower() == 'true'

# Ensure outputs directory exists before configuring logging
os.makedirs('outputs', exist_ok=True)

# Configure logging
def setup_logging(verbose: bool = False, debug: bool = False, no_output: bool = False) -> None:
    """Setup logging configuration."""
    log_level = logging.DEBUG if debug else (logging.INFO if verbose else logging.ERROR)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler (only if not no_output mode)
    if not no_output:
        # Create outputs directory if it doesn't exist
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler('outputs/music_metadata_fixer.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

# Supported music file extensions
MUSIC_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus',
    '.alac', '.aiff', '.dsd', '.dff', '.dsf'
}

class MusicRenamer:
    """Handles the renaming of music files with various cleanup operations."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False, metadata_only: bool = False, filename_only: bool = False, debug: bool = False, no_output: bool = False, albums_only: bool = False, max_depth: int = 10):
        """
        Initialize the MusicRenamer with configuration options.
        
        Args:
            dry_run: If True, show what would be done without making changes
            verbose: If True, enable verbose logging
            metadata_only: If True, only clean metadata tags, do not rename files
            filename_only: If True, only rename files, do not clean metadata tags
            debug: If True, enable debug logging
            no_output: If True, prevent generating output files
            albums_only: If True, only organize files into albums
            max_depth: Maximum depth for directory scanning
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.metadata_only = metadata_only
        self.filename_only = filename_only
        self.debug = debug
        self.no_output = no_output
        self.albums_only = albums_only
        self.max_depth = max_depth
        self._report_written = False
        
        # Initialize statistics
        self.stats = {
            'processed': 0,
            'renamed': 0,
            'metadata_updated': 0,
            'moved': 0,
            'skipped': 0,
            'errors': 0,
            'albums_created': 0
        }
        
        # Initialize collections
        self.replaced_urls = set()
        self.unique_files = set()
        self.file_actions = {}
        self.created_albums = []
        
        # Setup logging
        log_level = logging.DEBUG if debug else (logging.INFO if verbose else logging.ERROR)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('outputs/music_metadata_fixer.log'),
                logging.StreamHandler() if verbose or debug else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Compile regex patterns for efficiency
        self.leading_numbers_pattern = re.compile(r'^[\d\-_\.\[\]\s]+')
        self.website_pattern = re.compile(r'[-\s_]*([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.(com|co|in|net|ws|io))[-\s_]*', re.IGNORECASE)
        self.bitrate_pattern = re.compile(r'\s*\d+\s*[Kk]bps\s*', re.IGNORECASE)
        self.trailing_brackets_pattern = re.compile(r'\s*\[[^\]]*\]\s*$')
        self.empty_brackets_pattern = re.compile(r'\s*\[\s*\]\s*')
        self.multiple_spaces_pattern = re.compile(r'\s+')
        self.repeated_extensions_pattern = re.compile(r'\.([a-zA-Z0-9]+)\.\1$', re.IGNORECASE)
        self.trailing_separator_pattern = re.compile(r'[-\s_]+$')
        
        # Album mapping patterns
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        
        # Track original and final filenames for markdown table
        self.filename_changes = []
        
        # Track metadata changes for reporting
        self.metadata_changes = []
        
        self.file_actions = {}  # key: file path, value: dict with keys: rename, metadata, errors (list), dir
        
    def is_music_file(self, file_path: Path) -> bool:
        """Check if the file is a music file based on its extension."""
        return file_path.suffix.lower() in MUSIC_EXTENSIONS
    
    def clean_filename(self, filename: str) -> str:
        """
        Clean the filename by applying various transformations, but preserve [w+].ft and ft.[w+] patterns.
        """
        # Step 0: Remove repeated file extensions (e.g., .mp3.mp3 -> .mp3)
        filename = self.repeated_extensions_pattern.sub(r'.\1', filename)
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
            
            original_file_key = str(file_path.resolve())
            self.unique_files.add(original_file_key)
            
            # Initialize file_actions entry if it doesn't exist
            if original_file_key not in self.file_actions:
                self.file_actions[original_file_key] = {'rename': None, 'metadata': None, 'errors': [], 'dir': str(file_path.parent)}
            
            original_name = file_path.name
            filename_changed = False
            metadata_changed = False
            results = []
            current_file_path = file_path
            
            # Handle filename cleaning
            if not self.metadata_only:
                try:
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
                        self.file_actions[original_file_key]['rename'] = {
                            'original': original_name,
                            'final': new_path.name,
                            'path': str(file_path.parent)
                        }
                        
                        if self.dry_run:
                            self.logger.info(f"DRY RUN: Would rename '{original_name}' to '{new_path.name}'")
                        else:
                            file_path.rename(new_path)
                            self.logger.info(f"Renamed '{original_name}' to '{new_path.name}'")
                            current_file_path = new_path  # Update current_file_path for metadata processing
                        
                        filename_changed = True
                        results.append(f"filename: '{original_name}' → '{new_path.name}'")
                except Exception as e:
                    error_msg = f"Error during filename cleaning: {str(e)}"
                    self.logger.error(error_msg)
                    self.file_actions[original_file_key]['errors'].append(error_msg)
                    results.append(f"filename error: {error_msg}")
            
            # Handle metadata cleaning
            if not self.filename_only:
                try:
                    metadata_success, metadata_result = self.clean_metadata(current_file_path)
                    if metadata_success and "Metadata updated" in metadata_result:
                        metadata_changed = True
                        results.append(metadata_result)
                        # Track metadata changes for reporting
                        self.file_actions[original_file_key]['metadata'] = metadata_result.replace('Metadata updated: ', '')
                    elif not metadata_success:
                        results.append(f"metadata error: {metadata_result}")
                        self.file_actions[original_file_key]['errors'].append(metadata_result)
                except Exception as e:
                    error_msg = f"Error during metadata cleaning: {str(e)}"
                    self.logger.error(error_msg)
                    self.file_actions[original_file_key]['errors'].append(error_msg)
                    results.append(f"metadata error: {error_msg}")
            
            if filename_changed or metadata_changed:
                return True, "; ".join(results)
            else:
                return True, "No changes needed"
            
        except Exception as e:
            import traceback
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            # Ensure file_actions entry exists before trying to append error
            original_file_key = str(file_path.resolve())
            if original_file_key not in self.file_actions:
                self.file_actions[original_file_key] = {'rename': None, 'metadata': None, 'errors': [], 'dir': str(file_path.parent)}
            
            # Track error details for reporting
            self.file_actions[original_file_key]['errors'].append(str(e))
            return False, error_msg
    
    def process_directory(self, directory_path: Path) -> None:
        """
        Recursively process all music files in the directory until no more changes are needed.
        
        Args:
            directory_path: Path to the directory to process
        """
        if self.albums_only:
            # Handle album-only processing
            self.process_directory_for_albums(directory_path)
            return
            
        if not directory_path.exists():
            self.logger.error(f"Directory does not exist: {directory_path}")
            return
        
        if not directory_path.is_dir():
            self.logger.error(f"Path is not a directory: {directory_path}")
            return
        
        self.logger.info(f"Processing directory: {directory_path} (max depth: {self.max_depth})")
        
        # Track total changes across all passes
        total_passes = 0
        total_changes = 0
        
        # For dry-run mode, track virtual file states
        virtual_files = {}
        
        while True:
            pass_number = total_passes + 1
            self.logger.info(f"Starting pass {pass_number}...")
            
            # Reset stats for this pass
            pass_stats = {
                'processed': 0,
                'renamed': 0,
                'metadata_updated': 0,
                'errors': 0,
                'skipped': 0
            }
            
            changes_in_pass = 0
            
            # Get all music files with depth limit
            music_files = self.walk_with_depth_limit(directory_path)
            
            for file_path in music_files:
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
                    self.logger.debug(f"Processed: {file_path} - {result}")
            
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
                self.logger.info(f"Pass {pass_number} completed: {changes_in_pass} changes made")
                if self.verbose:
                    self.logger.info(f"  - Files renamed: {pass_stats['renamed']}")
                    self.logger.info(f"  - Metadata updated: {pass_stats['metadata_updated']}")
                    self.logger.info(f"  - Files skipped: {pass_stats['skipped']}")
                    self.logger.info(f"  - Errors: {pass_stats['errors']}")
            else:
                self.logger.info(f"Pass {pass_number} completed: No changes needed")
                break
            
            # Safety check to prevent infinite loops
            if total_passes > 10:
                self.logger.warning(f"Reached maximum number of passes ({total_passes}). Stopping to prevent infinite loop.")
                break
        
        self.logger.info(f"Processing completed after {total_passes} passes with {total_changes} total changes")
    
    def print_stats(self) -> None:
        """Print processing statistics."""
        # Always print summary to console
        print("=" * 50)
        if self.albums_only:
            print("ALBUM MAPPING STATISTICS")
        else:
            print("PROCESSING STATISTICS")
        print("=" * 50)
        
        # Use the appropriate counter based on processing mode
        if self.albums_only:
            total_processed = self.stats['processed']
        else:
            total_processed = len(self.unique_files)
            
        print(f"Total files processed: {total_processed}")
        
        if not self.albums_only:
            print(f"Files renamed: {self.stats['renamed']}")
            print(f"Metadata updated: {self.stats['metadata_updated']}")
        else:
            print(f"Files moved: {self.stats['moved']}")
            print(f"Albums created: {self.stats['albums_created']}")
            
        print(f"Files skipped: {self.stats['skipped']}")
        print(f"Errors encountered: {self.stats['errors']}")
        print("=" * 50)
        
        # Also log to file if verbose mode is enabled
        if self.verbose or self.debug:
            self.logger.info("=" * 50)
            if self.albums_only:
                self.logger.info("ALBUM MAPPING STATISTICS")
            else:
                self.logger.info("PROCESSING STATISTICS")
            self.logger.info("=" * 50)
            
            self.logger.info(f"Total files processed: {total_processed}")
            
            if not self.albums_only:
                self.logger.info(f"Files renamed: {self.stats['renamed']}")
                self.logger.info(f"Metadata updated: {self.stats['metadata_updated']}")
            else:
                self.logger.info(f"Files moved: {self.stats['moved']}")
                self.logger.info(f"Albums created: {self.stats['albums_created']}")
                
            self.logger.info(f"Files skipped: {self.stats['skipped']}")
            self.logger.info(f"Errors encountered: {self.stats['errors']}")
            self.logger.info("=" * 50)
    
    def write_urls_to_file(self, album_results=None) -> None:
        """Write the processing results to a professional markdown report file with a timestamped filename."""
        # Prevent multiple report writes during the same runtime
        if self._report_written:
            self.logger.debug("Report already written during this runtime, skipping...")
            return
        if self.no_output:
            return
        if not self.replaced_urls and not self.file_actions and not album_results:
            return
        try:
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            timestamp_for_file = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = outputs_dir / f"replaced_urls-{timestamp_for_file}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                # Professional Header
                f.write("# 🎵 Music Metadata Fixer Report\n")
                f.write(f"**Processed on:** {timestamp}\n\n")
                f.write("> This report summarizes all actions taken to clean and organize your music files, including renames, metadata updates, album organization, and any errors encountered.\n\n")
                f.write("---\n\n")
                # Table of Contents
                f.write("## Table of Contents\n\n")
                f.write("- [Summary](#summary)\n")
                f.write("- [File Renames](#file-renames)\n")
                f.write("- [Metadata Updates](#metadata-updates)\n")
                f.write("- [Errors](#errors)\n\n")
                # Summary
                f.write("## Summary\n\n")
                f.write("A high-level overview of the processing results.\n\n")
                f.write("| Metric | Count |\n")
                f.write("|--------|-------|\n")
                f.write(f"| Total Files Processed | {len(self.unique_files)} |\n")
                renamed_count = sum(1 for actions in self.file_actions.values() if actions['rename'])
                metadata_count = sum(1 for actions in self.file_actions.values() if actions['metadata'])
                error_count = sum(1 for actions in self.file_actions.values() if actions['errors'])
                f.write(f"| Files Renamed | {renamed_count} |\n")
                f.write(f"| Files with Metadata Updated | {metadata_count} |\n")
                f.write(f"| Files with Errors | {error_count} |\n")
                if self.replaced_urls:
                    f.write(f"| Unique URLs Replaced | {len(self.replaced_urls)} |\n")
                if album_results:
                    f.write(f"| Albums Created | {len(album_results)} |\n")
                if self.dry_run:
                    f.write("\n> **Note:** This was a dry run - no files were actually modified.\n")
                f.write("\n---\n\n")
                # File Renames
                f.write("## File Renames\n\n")
                f.write("All files that were renamed during processing.\n\n")
                renamed_files = [(file_path, actions) for file_path, actions in self.file_actions.items() if actions['rename']]
                if renamed_files:
                    f.write("| Original Name | Name After Rename | Path |\n")
                    f.write("|--------------|-------------------|------|\n")
                    for file_path, actions in renamed_files:
                        original = actions['rename']['original']
                        final = actions['rename']['final']
                        path = actions['rename']['path']
                        f.write(f"| `{original}` | `{final}` | `{path}` |\n")
                else:
                    f.write("No files were renamed.\n")
                f.write("\n---\n\n")
                # Metadata Updates
                f.write("## Metadata Updates\n\n")
                f.write("Files whose metadata tags were updated.\n\n")
                metadata_files = [(file_path, actions) for file_path, actions in self.file_actions.items() if actions['metadata']]
                if metadata_files:
                    f.write("| File Name After Rename | Metadata Changes |\n")
                    f.write("|-----------------------|------------------|\n")
                    for file_path, actions in metadata_files:
                        filename2 = actions['rename']['final'] if actions['rename'] else file_path.split('/')[-1]
                        changes = actions['metadata'].replace('|', '\|')
                        f.write(f"| `{filename2}` | {changes} |\n")
                else:
                    f.write("No metadata updates.\n")
                f.write("\n---\n\n")
                # Errors
                f.write("## Errors\n\n")
                f.write("Any errors encountered during processing.\n\n")
                error_files = [(file_path, actions) for file_path, actions in self.file_actions.items() if actions['errors']]
                if error_files:
                    f.write("| File Name | Error Message |\n")
                    f.write("|-----------|--------------|\n")
                    for file_path, actions in error_files:
                        filename2 = actions['rename']['final'] if actions['rename'] else file_path.split('/')[-1]
                        error_msgs = actions['errors']
                        if isinstance(error_msgs, list):
                            for error_msg in error_msgs:
                                f.write(f"| `{filename2}` | {error_msg} |\n")
                        else:
                            f.write(f"| `{filename2}` | {error_msgs} |\n")
                else:
                    f.write("No errors encountered.\n")
                f.write("\n---\n\n")
                # Footer
                f.write("_Report generated by Music Metadata Fixer. For support or feedback, contact the maintainer._\n")
            self._report_written = True
            self.logger.info(f"Report written to: {filename}")
        except Exception as e:
            self.logger.error(f"Error writing report to file: {str(e)}")
    
    def clean_text(self, text: str, is_album: bool = False) -> str:
        """
        Clean text using the same rules as filename cleaning, but preserve [w+].ft and ft.[w+] patterns.
        For album names, preserve leading numbers that are not years (1900+).
        
        Args:
            text: Text to clean
            is_album: If True, preserve leading numbers in album names
        """
        # Ensure text is a string
        if text is None:
            return ""
        
        # Convert to string if it's not already
        if not isinstance(text, str):
            text = str(text)
        
        if not text:
            return text
        preserved = []
        def preserve_ft(match):
            preserved.append(match.group(0))
            return f"__FTPRESERVE{len(preserved)-1}__"
        ft_pattern = re.compile(r'(\[[^\]]+\]\.ft|ft\.\[[^\]]+\])', re.IGNORECASE)
        text = ft_pattern.sub(preserve_ft, text)
        
        # Only remove leading numbers if this is not an album name
        if not is_album:
            text = self.leading_numbers_pattern.sub('', text)
        
        original_text = text
        text = self.website_pattern.sub('', text)
        if text != original_text:
            matches = self.website_pattern.findall(original_text)
            for match in matches:
                # findall() returns tuples when regex has groups, so extract the first group
                if isinstance(match, tuple):
                    match = match[0]  # Take the first group (the domain name)
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
                    try:
                        audio.save()
                        self.logger.info(f"Updated metadata for {file_path.name}: {', '.join(changes_log)}")
                    except Exception as save_error:
                        return False, f"Error saving metadata: {str(save_error)}"
                else:
                    self.logger.info(f"DRY RUN: Would update metadata for {file_path.name}: {', '.join(changes_log)}")
                
                return True, f"Metadata updated: {', '.join(changes_log)}"
            else:
                return True, "No metadata changes needed"
                
        except Exception as e:
            import traceback
            error_msg = f"Error processing metadata for {file_path}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"Metadata error traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def _clean_id3_tags(self, tags, changes_log: List[str]) -> Tuple[bool, List[str]]:
        """Clean ID3 tags (MP3 files)."""
        changes_made = False
        # Clean title
        if 'TIT2' in tags:
            # Properly extract text from ID3 tag
            title_tag = tags['TIT2']
            if hasattr(title_tag, 'text'):
                original_title = title_tag.text[0] if title_tag.text else ''
            else:
                original_title = str(title_tag)
            cleaned_title = self.clean_text(original_title)
            if cleaned_title != original_title:
                if not self.dry_run:
                    tags['TIT2'] = TIT2(encoding=3, text=cleaned_title)
                changes_log.append(f"title: '{original_title}' → '{cleaned_title}'")
                changes_made = True
        # Clean artist
        if 'TPE1' in tags:
            # Properly extract text from ID3 tag
            artist_tag = tags['TPE1']
            if hasattr(artist_tag, 'text'):
                original_artist = artist_tag.text[0] if artist_tag.text else ''
            else:
                original_artist = str(artist_tag)
            cleaned_artist = self.clean_text(original_artist)
            if cleaned_artist != original_artist:
                if not self.dry_run:
                    tags['TPE1'] = TPE1(encoding=3, text=cleaned_artist)
                changes_log.append(f"artist: '{original_artist}' → '{cleaned_artist}'")
                changes_made = True
        # Clean album (preserve leading numbers)
        if 'TALB' in tags:
            # Properly extract text from ID3 tag
            album_tag = tags['TALB']
            if hasattr(album_tag, 'text'):
                original_album = album_tag.text[0] if album_tag.text else ''
            else:
                original_album = str(album_tag)
            cleaned_album = self.clean_text(original_album, is_album=True)
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
        # Clean album (preserve leading numbers)
        if 'album' in tags:
            original_album = tags['album'][0]
            cleaned_album = self.clean_text(original_album, is_album=True)
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
        # Clean album (preserve leading numbers)
        if tags.getAttribute('WM/AlbumTitle'):
            original_album = tags.getAttribute('WM/AlbumTitle')[0]
            cleaned_album = self.clean_text(original_album, is_album=True)
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
        # Clean album (preserve leading numbers)
        if '\xa9alb' in tags:
            original_album = tags['\xa9alb'][0]
            cleaned_album = self.clean_text(original_album, is_album=True)
            if cleaned_album != original_album:
                if not self.dry_run:
                    tags['\xa9alb'] = [cleaned_album]
                changes_log.append(f"album: '{original_album}' → '{cleaned_album}'")
                changes_made = True
        # Do NOT clean composer or other fields
        return changes_made, changes_log

    # Album mapping methods
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
            # Ensure album_name and year are strings, not tuples
            if isinstance(album_name, tuple):
                album_name = album_name[0] if album_name else ''
            if isinstance(year, tuple):
                year = year[0] if year else ''
            return {'album': album_name, 'year': year}
        
        except Exception as e:
            self.logger.warning(f"Error extracting metadata from {file_path}: {str(e)}")
            return {'album': 'Unknown Album', 'year': ''}
    
    def _extract_id3_metadata(self, tags) -> Tuple[str, str]:
        """Extract album and year from ID3 tags (MP3 files)."""
        album_name = 'Unknown Album'
        year = ''
        
        if 'TALB' in tags:
            # Properly extract text from ID3 tag
            album_tag = tags['TALB']
            if hasattr(album_tag, 'text'):
                album_name = album_tag.text[0] if album_tag.text else 'Unknown Album'
            else:
                album_name = str(album_tag)
        
        # Try different year fields
        if 'TDRC' in tags:
            year_tag = tags['TDRC']
            if hasattr(year_tag, 'text'):
                year = year_tag.text[0] if year_tag.text else ''
            else:
                year = str(year_tag)
        elif 'TYER' in tags:
            year_tag = tags['TYER']
            if hasattr(year_tag, 'text'):
                year = year_tag.text[0] if year_tag.text else ''
            else:
                year = str(year_tag)
        
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
        # If album_name is a tuple, take the first element
        if isinstance(album_name, tuple):
            album_name = album_name[0] if album_name else ''
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
        Create album folder name with year if available.
        
        Args:
            album_name: Album name
            year: Year string
            
        Returns:
            Album folder name
        """
        if year:
            # Check if year is already in album name to avoid duplication
            if year not in album_name:
                return f"{album_name} ({year})"
            else:
                return album_name
        else:
            return album_name
    
    def process_album_file(self, file_path: Path, source_directory: Path) -> Tuple[bool, str]:
        """
        Process a single music file for album organization.
        
        Args:
            file_path: Path to the music file
            source_directory: Source directory for album organization
            
        Returns:
            Tuple of (success, result_message)
        """
        try:
            if not self.is_music_file(file_path):
                return False, "Not a music file"
            
            # Extract metadata
            try:
                metadata = self.extract_metadata(file_path)
                album_name = self.clean_album_name(metadata['album'])
                year = self.extract_year(metadata['year'])
                album_folder_name = self.create_album_folder_name(album_name, year)
            except Exception as e:
                error_msg = f"Error extracting metadata: {str(e)}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Create album folder path
            album_folder = source_directory / album_folder_name
            
            # Create album folder if it doesn't exist
            if not album_folder.exists():
                if self.dry_run:
                    self.logger.info(f"DRY RUN: Would create album folder: {album_folder}")
                else:
                    try:
                        album_folder.mkdir(parents=True, exist_ok=True)
                        self.logger.info(f"Created album folder: {album_folder}")
                        self.stats['albums_created'] += 1
                        if album_folder_name not in self.created_albums:
                            self.created_albums.append(album_folder_name)
                    except Exception as e:
                        error_msg = f"Error creating album folder: {str(e)}"
                        self.logger.error(error_msg)
                        return False, error_msg
            
            # Move file to album folder
            dest_file = album_folder / file_path.name
            
            # Handle filename conflicts
            if dest_file.exists() and dest_file != file_path:
                counter = 1
                while dest_file.exists():
                    name_without_ext, ext = os.path.splitext(file_path.name)
                    new_name = f"{name_without_ext} ({counter}){ext}"
                    dest_file = album_folder / new_name
                    counter += 1
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would move '{file_path.name}' to '{album_folder_name}/'")
            else:
                try:
                    shutil.move(str(file_path), str(dest_file))
                    self.logger.info(f"Moved '{file_path.name}' to '{album_folder_name}/'")
                except Exception as e:
                    error_msg = f"Error moving file: {str(e)}"
                    self.logger.error(error_msg)
                    return False, error_msg
            
            return True, f"Moved to {album_folder_name}/"
            
        except Exception as e:
            import traceback
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"Album processing error traceback: {traceback.format_exc()}")
            # Track error details for reporting
            self.error_details.append({
                'filename': file_path.name,
                'path': str(file_path.parent),
                'error': str(e)
            })
            return False, error_msg
    
    def process_directory_for_albums(self, directory_path: Path) -> None:
        """
        Organize music files into album folders, but skip album organization for files in Devotional folders.
        """
        # Group files by album (excluding Devotional)
        music_files = self.walk_with_depth_limit(directory_path, self.max_depth)
        albums = {}
        devotional_files = []
        for file_path in music_files:
            # Check if file is in a Devotional folder
            if any(part.lower() == 'devotional' for part in file_path.parts):
                devotional_files.append(file_path)
                continue
            try:
                metadata = self.extract_metadata(file_path)
                album_name = self.clean_album_name(metadata['album'])
                year = self.extract_year(metadata['year'])
                album_key = f"{album_name} ({year})" if year else album_name
                if album_key not in albums:
                    albums[album_key] = []
                albums[album_key].append(file_path)
            except Exception as e:
                self.stats['processed'] += 1
                self.stats['errors'] += 1
                self.logger.error(f"Error extracting metadata for {file_path}: {e}")
        # Process Devotional files: only rename/clean metadata, do not organize
        for file_path in devotional_files:
            self.stats['processed'] += 1
            self.process_file(file_path)
        # Process albums as usual for non-Devotional files
        for album_key, files in albums.items():
            if len(files) <= 3:
                for file_path in files:
                    self.stats['processed'] += 1
                    self.stats['skipped'] += 1
                    if self.verbose:
                        self.logger.debug(f"Skipped album (<=3 songs): {file_path.name} (album: {album_key})")
                    self.logger.info(f"Album '{album_key}' has {len(files)} song(s) - leaving in current directory")
            else:
                self.logger.info(f"Album '{album_key}' with {len(files)} songs - moving to album folder")
                for file_path in files:
                    self.stats['processed'] += 1
                    success, result = self.process_album_file(file_path, directory_path)
                    if success:
                        self.stats['moved'] += 1
                    else:
                        self.stats['errors'] += 1
                    if self.verbose:
                        self.logger.debug(f"Processed: {file_path} - {result}")
    
    def get_created_albums(self):
        """Return the list of created album folder names."""
        return self.created_albums

    def walk_with_depth_limit(self, directory_path: Path, max_depth: int = None) -> List[Path]:
        """
        Walk through directory with a depth limit and return all music files found.
        
        Args:
            directory_path: Root directory to start from
            max_depth: Maximum depth to scan (default: self.max_depth)
            
        Returns:
            List of Path objects for all music files found within the depth limit
        """
        if max_depth is None:
            max_depth = self.max_depth
            
        music_files = []
        
        def walk_recursive(current_path: Path, current_depth: int):
            if current_depth > max_depth:
                return
                
            try:
                for item in current_path.iterdir():
                    if item.is_file() and self.is_music_file(item):
                        music_files.append(item)
                    elif item.is_dir() and not item.name.startswith('.'):
                        walk_recursive(item, current_depth + 1)
            except PermissionError:
                self.logger.warning(f"Permission denied accessing: {current_path}")
            except Exception as e:
                self.logger.warning(f"Error accessing {current_path}: {e}")
        
        walk_recursive(directory_path, 0)
        return music_files

    def delete_empty_folders(self, directory_path: Path) -> int:
        """
        Recursively delete empty folders starting from the given directory.
        
        Args:
            directory_path: Root directory to start checking from
            
        Returns:
            Number of empty folders deleted
        """
        deleted_count = 0
        
        def delete_empty_recursive(current_path: Path) -> bool:
            """Recursively check and delete empty folders."""
            nonlocal deleted_count
            
            if not current_path.exists() or not current_path.is_dir():
                return False
                
            # Check if this is a Devotional folder - don't delete it
            if current_path.name.lower() == 'devotional':
                return True
                
            # First, recursively process subdirectories
            subdirs_empty = True
            for item in current_path.iterdir():
                if item.is_dir():
                    if not delete_empty_recursive(item):
                        subdirs_empty = False
                else:
                    subdirs_empty = False
                    
            # If all subdirectories are empty and no files remain, delete this directory
            if subdirs_empty and not any(current_path.iterdir()):
                try:
                    if not self.dry_run:
                        current_path.rmdir()
                        self.logger.info(f"Deleted empty folder: {current_path}")
                    else:
                        self.logger.info(f"[DRY RUN] Would delete empty folder: {current_path}")
                    deleted_count += 1
                    return True
                except Exception as e:
                    self.logger.warning(f"Failed to delete empty folder {current_path}: {e}")
                    return False
            else:
                return False
                
        delete_empty_recursive(directory_path)
        return deleted_count

def main():
    """Main function to handle command line arguments and execute the renaming process."""
    parser = argparse.ArgumentParser(
        description="Clean up music file names and metadata by removing leading numbers, website details, and trailing spaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python music_metadata_fixer.py /path/to/music/folder
  python music_metadata_fixer.py . --dry-run --verbose
  python music_metadata_fixer.py /music --dry-run
  python music_metadata_fixer.py /music --metadata-only --dry-run
  python music_metadata_fixer.py /music --filename-only --verbose
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
    
    parser.add_argument(
        '--albums-only',
        action='store_true',
        help='Only process albums, do not rename files or clean metadata'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=10,
        help='Maximum directory depth to scan for music files (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Setup logging first
    setup_logging(verbose=args.verbose, debug=args.debug, no_output=args.no_output)
    
    # Validate arguments
    if args.metadata_only and args.filename_only:
        print("Cannot use both --metadata-only and --filename-only")
        return 1
    
    if args.albums_only and (args.metadata_only or args.filename_only):
        print("Cannot use --albums-only with --metadata-only or --filename-only")
        return 1
    
    if args.max_depth < 0:
        print("Max depth must be non-negative")
        return 1
    
    # Check if mutagen is available for metadata operations
    if not args.filename_only and not args.albums_only and not MUTAGEN_AVAILABLE:
        print("Mutagen library not available. Install with: pip install mutagen")
        print("Metadata cleaning will be skipped. Use --filename-only to continue with filename cleaning only.")
        if not args.metadata_only:
            print("Continuing with filename cleaning only...")
            args.filename_only = True
        else:
            print("Cannot perform metadata-only operations without mutagen library")
            return 1
    
    # Create and run the renamer
    renamer = MusicRenamer(
        dry_run=args.dry_run, 
        verbose=args.verbose, 
        metadata_only=args.metadata_only, 
        filename_only=args.filename_only,
        debug=args.debug,
        no_output=args.no_output,
        albums_only=args.albums_only,
        max_depth=args.max_depth
    )
    
    try:
        directory_path = Path(args.directory).resolve()
        
        # Show start message
        if args.albums_only:
            print(f"Starting album organization for: {directory_path}")
        else:
            print(f"Starting music file processing for: {directory_path}")
        
        if args.dry_run:
            print("[DRY RUN MODE - No actual changes will be made]")
        
        # Process the directory
        if args.albums_only:
            renamer.process_directory_for_albums(directory_path)
        else:
            renamer.process_directory(directory_path)
            
        # Delete empty folders after processing
        if not args.dry_run:
            deleted_folders = renamer.delete_empty_folders(directory_path)
            if deleted_folders > 0:
                print(f"\nDeleted {deleted_folders} empty folder(s)")
        else:
            deleted_folders = renamer.delete_empty_folders(directory_path)
            if deleted_folders > 0:
                print(f"\n[DRY RUN] Would delete {deleted_folders} empty folder(s)")
            
        # Print statistics
        renamer.print_stats()
        
        # Generate report
        if not args.no_output:
            if args.albums_only:
                renamer.write_urls_to_file(renamer.created_albums)
            else:
                renamer.write_urls_to_file()
            print(f"\nReport generated: outputs/replaced_urls-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md")
        
        print("\nAll operations completed!")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if args.verbose or args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    exit(main()) 