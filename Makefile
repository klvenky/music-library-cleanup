# Music Metadata Fixer Makefile
# Provides easy access to music file operations

.PHONY: help install clean test rename rename-dry-run metadata metadata-dry-run albums albums-dry-run all all-dry-run test-run

# Default target
help:
	@echo "Music Metadata Fixer - Available Operations"
	@echo "=========================================="
	@echo ""
	@echo "Installation:"
	@echo "  install          Install required dependencies"
	@echo ""
	@echo "File Renaming:"
	@echo "  rename           Rename music files (recursive cleaning)"
	@echo "  rename-dry-run   Preview file renaming without making changes"
	@echo ""
	@echo "Metadata Cleaning:"
	@echo "  metadata         Clean metadata tags in music files"
	@echo "  metadata-dry-run Preview metadata cleaning without making changes"
	@echo ""
	@echo "Album Organization:"
	@echo "  albums           Organize music files into album folders"
	@echo "  albums-dry-run   Preview album organization without making changes"
	@echo ""
	@echo "Combined Operations:"
	@echo "  all              Run all operations (rename + metadata + albums)"
	@echo "  all-dry-run      Preview all operations without making changes"
	@echo ""
	@echo "Utility:"
	@echo "  clean            Remove test files and logs"
	@echo "  test             Create test files in test_music/ directory"
	@echo "  test-run         Run tests on test_music directory (no output files generated)"
	@echo ""
	@echo "Usage Examples:"
	@echo "  make rename DIRECTORY=/path/to/music"
	@echo "  make metadata DIRECTORY=/path/to/music --dry-run"
	@echo "  make albums DIRECTORY=/path/to/music --verbose"

# Installation
install:
	@echo "Installing required dependencies..."
	pip3 install mutagen
	@echo "Dependencies installed successfully!"

# File renaming operations
rename:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make rename DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Renaming music files in $(DIRECTORY)..."
	python3 music_renamer.py "$(DIRECTORY)" --verbose

rename-dry-run:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make rename-dry-run DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Previewing file renaming in $(DIRECTORY)..."
	python3 music_renamer.py "$(DIRECTORY)" --dry-run --verbose

# Metadata cleaning operations
metadata:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make metadata DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Cleaning metadata in $(DIRECTORY)..."
	python3 music_renamer.py "$(DIRECTORY)" --metadata-only --verbose

metadata-dry-run:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make metadata-dry-run DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Previewing metadata cleaning in $(DIRECTORY)..."
	python3 music_renamer.py "$(DIRECTORY)" --metadata-only --dry-run --verbose

# Album organization operations
albums:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make albums DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Organizing albums in $(DIRECTORY)..."
	python3 album_mapper.py "$(DIRECTORY)" --verbose

albums-dry-run:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make albums-dry-run DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Previewing album organization in $(DIRECTORY)..."
	python3 album_mapper.py "$(DIRECTORY)" --dry-run --verbose

# Combined operations
all:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make all DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Running all operations in $(DIRECTORY)..."
	@echo "Step 1: Renaming files..."
	python3 music_renamer.py "$(DIRECTORY)" --verbose
	@echo "Step 2: Cleaning metadata..."
	python3 music_renamer.py "$(DIRECTORY)" --metadata-only --verbose
	@echo "Step 3: Organizing albums..."
	python3 album_mapper.py "$(DIRECTORY)" --verbose
	@echo "All operations completed!"

all-dry-run:
	@if [ -z "$(DIRECTORY)" ]; then \
		echo "Error: DIRECTORY not specified. Usage: make all-dry-run DIRECTORY=/path/to/music"; \
		exit 1; \
	fi
	@echo "Previewing all operations in $(DIRECTORY)..."
	@echo "Step 1: Previewing file renaming..."
	python3 music_renamer.py "$(DIRECTORY)" --dry-run --verbose
	@echo "Step 2: Previewing metadata cleaning..."
	python3 music_renamer.py "$(DIRECTORY)" --metadata-only --dry-run --verbose
	@echo "Step 3: Previewing album organization..."
	python3 album_mapper.py "$(DIRECTORY)" --dry-run --verbose
	@echo "All preview operations completed!"

# Utility operations
clean:
	@echo "Cleaning up test files and logs..."
	rm -rf test_music/
	rm -f *.log
	@echo "Cleanup completed!"

test:
	@echo "Creating test files..."
	mkdir -p test_music
	cd test_music && touch "01 - [2023] Artist - Song [Remix] [].mp3" "123_www.example.com_Track [Live] [].flac" "  05-Artist-Song  [].wav"
	@echo "Test files created in test_music/ directory"
	@echo "You can now run: make rename-dry-run DIRECTORY=test_music --no-output"

test-run:
	@echo "Running tests on test_music directory..."
	@echo "Testing file renaming..."
	python3 music_renamer.py test_music --dry-run --verbose --no-output
	@echo "Testing metadata cleaning..."
	python3 music_renamer.py test_music --metadata-only --dry-run --verbose --no-output
	@echo "Testing album organization..."
	python3 album_mapper.py test_music --dry-run --verbose --no-output
	@echo "All tests completed!" 