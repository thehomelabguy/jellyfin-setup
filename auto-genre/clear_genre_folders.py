#!/usr/bin/env python3
"""
Clear Genre Folders Script

This script safely removes all symlinks from the genre folders while preserving
the folder structure. It only removes symlinks, not actual files or directories.
"""

import os
import sys
from pathlib import Path

def load_config():
    """Load configuration from config.env file."""
    config = {}
    config_file = Path(__file__).parent / "config.env"
    
    if not config_file.exists():
        print(f"Error: Configuration file {config_file} not found!")
        print("Please create config.env with your settings.")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    return config

def parse_path_mapping(path_config):
    """Parse host:container path mapping from config value."""
    if ':' in path_config:
        host_path, container_path = path_config.split(':', 1)
        return host_path.strip(), container_path.strip()
    else:
        # If no colon, assume it's just a host path
        return path_config.strip(), path_config.strip()

def clear_symlinks_in_directory(directory_path):
    """Remove all symlinks in a directory and its subdirectories."""
    if not os.path.exists(directory_path):
        print(f"Directory {directory_path} does not exist, skipping")
        return 0, 0
    
    print(f"\nClearing symlinks in: {directory_path}")
    print("=" * 60)
    
    total_symlinks = 0
    removed_symlinks = 0
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(directory_path):
        # Get the genre folder name (relative to base directory)
        relative_path = os.path.relpath(root, directory_path)
        if relative_path == '.':
            genre_name = "root"
        else:
            genre_name = relative_path
        
        symlinks_in_genre = 0
        
        # Check each item in the directory
        for item in files + dirs:  # Check both files and directories
            item_path = os.path.join(root, item)
            
            if os.path.islink(item_path):
                total_symlinks += 1
                symlinks_in_genre += 1
                
                try:
                    # Get the target (for logging purposes)
                    try:
                        target = os.readlink(item_path)
                        print(f"  Removing: {item} -> {target}")
                    except OSError:
                        print(f"  Removing broken symlink: {item}")
                    
                    # Remove the symlink
                    os.unlink(item_path)
                    removed_symlinks += 1
                    
                except Exception as e:
                    print(f"  Error removing {item}: {e}")
        
        if symlinks_in_genre > 0:
            print(f"Genre '{genre_name}': Removed {symlinks_in_genre} symlinks")
    
    print(f"\nSummary for {os.path.basename(directory_path)}:")
    print(f"  Total symlinks found: {total_symlinks}")
    print(f"  Symlinks removed: {removed_symlinks}")
    
    return total_symlinks, removed_symlinks

def main():
    """Main function."""
    print("Genre Folders Cleaner")
    print("=" * 40)
    print("This script will remove all symlinks from genre folders")
    print("while preserving the folder structure.")
    print()
    
    # Load configuration
    config = load_config()
    print("Configuration loaded from config.env")
    
    # Parse path mappings (we only need the host paths for local operations)
    genres_dir_1_host, _ = parse_path_mapping(config.get('GENRES_DIR_1', ''))
    genres_dir_2_host, _ = parse_path_mapping(config.get('GENRES_DIR_2', ''))
    
    if not genres_dir_1_host and not genres_dir_2_host:
        print("Error: No genre directories configured in config.env")
        sys.exit(1)
    
    print(f"Genre directories to clear:")
    if genres_dir_1_host:
        print(f"  - {genres_dir_1_host}")
    if genres_dir_2_host:
        print(f"  - {genres_dir_2_host}")
    
    # Confirm with user
    print()
    response = input("Are you sure you want to remove all symlinks? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("Operation cancelled.")
        sys.exit(0)
    
    print("\nStarting symlink removal...")
    
    total_found = 0
    total_removed = 0
    
    # Clear first directory
    if genres_dir_1_host:
        found, removed = clear_symlinks_in_directory(genres_dir_1_host)
        total_found += found
        total_removed += removed
    
    # Clear second directory
    if genres_dir_2_host:
        found, removed = clear_symlinks_in_directory(genres_dir_2_host)
        total_found += found
        total_removed += removed
    
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total symlinks found: {total_found}")
    print(f"Total symlinks removed: {total_removed}")
    
    if total_removed > 0:
        print(f"\n✓ Successfully cleared {total_removed} symlinks from genre folders!")
        print("The genre folder structure has been preserved.")
        print("You can now run the symlink creation script to generate new absolute symlinks.")
    else:
        print("\nNo symlinks were found to remove.")

if __name__ == "__main__":
    main()
