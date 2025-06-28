#!/bin/bash

# Music File Renamer Script
# Wrapper script for the Python music renamer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Music File Renamer"
    echo ""
    echo "Usage: $0 [OPTIONS] [DIRECTORY]"
    echo ""
    echo "Options:"
    echo "  -d, --dry-run       Show what would be renamed/modified without actually making changes"
    echo "  -v, --verbose       Enable verbose logging"
    echo "  -m, --metadata-only Only clean metadata tags, do not rename files"
    echo "  -f, --filename-only Only rename files, do not clean metadata tags"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/music/folder"
    echo "  $0 . --dry-run --verbose"
    echo "  $0 /music --dry-run"
    echo "  $0 /music --metadata-only --dry-run"
    echo "  $0 /music --filename-only --verbose"
    echo ""
}

# Check if Python 3 is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        print_info "Please install Python 3 and try again."
        exit 1
    fi
}

# Check if the Python script exists
check_script() {
    if [ ! -f "music_renamer.py" ]; then
        print_error "music_renamer.py not found in current directory."
        print_info "Please make sure you're running this script from the correct directory."
        exit 1
    fi
}

# Main script logic
main() {
    # Parse command line arguments
    PYTHON_ARGS=""
    DIRECTORY="."
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--dry-run)
                PYTHON_ARGS="$PYTHON_ARGS --dry-run"
                shift
                ;;
            -v|--verbose)
                PYTHON_ARGS="$PYTHON_ARGS --verbose"
                shift
                ;;
            -m|--metadata-only)
                PYTHON_ARGS="$PYTHON_ARGS --metadata-only"
                shift
                ;;
            -f|--filename-only)
                PYTHON_ARGS="$PYTHON_ARGS --filename-only"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                DIRECTORY="$1"
                shift
                ;;
        esac
    done
    
    # Check prerequisites
    check_python
    check_script
    
    # Make the Python script executable
    chmod +x music_renamer.py
    
    print_info "Starting music file renaming process..."
    print_info "Directory: $DIRECTORY"
    
    if [[ $PYTHON_ARGS == *"--dry-run"* ]]; then
        print_warning "DRY RUN MODE - No files will be actually renamed"
    fi
    
    # Run the Python script
    if python3 music_renamer.py "$DIRECTORY" $PYTHON_ARGS; then
        print_success "Music file renaming completed successfully!"
    else
        print_error "Music file renaming failed!"
        exit 1
    fi
}

# Run main function with all arguments
main "$@" 