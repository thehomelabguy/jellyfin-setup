#!/usr/bin/env python3
"""
Genre Symlink Creator

This script scans movies and TV shows from configured directories, gets their genres from Jellyfin,
and creates symlinks in the appropriate genre folders.
"""

import os
import sys
import json
import re
import shutil
from pathlib import Path
from jellyfin_apiclient_python import JellyfinClient
import requests

def load_config():
    """Load configuration from .env file."""
    config = {}
    config_file = Path(__file__).parent / ".env"
    
    if not config_file.exists():
        print(f"Error: Configuration file {config_file} not found!")
        print("Please create .env with your settings.")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    # Convert boolean values
    if 'INCLUDE_SHOWS' in config:
        config['INCLUDE_SHOWS'] = config['INCLUDE_SHOWS'].lower() in ('true', '1', 'yes', 'on')
    
    return config

def parse_path_mapping(path_config):
    """Parse host:container path mapping from config value."""
    if ':' in path_config:
        host_path, container_path = path_config.split(':', 1)
        return host_path.strip(), container_path.strip()
    else:
        # If no colon, assume it's just a host path
        return path_config.strip(), path_config.strip()

def get_jellyfin_client_and_auth(server_url, username, password):
    """Get authenticated Jellyfin client and auth token."""
    try:
        # Initialize and authenticate client
        client = get_jellyfin_client(server_url, username, password)
        if not client:
            return None, None, None
        
        # Extract auth info
        auth_token = client.config.data.get('auth.token')
        user_id = client.auth.jellyfin_user_id()
        
        return client, auth_token, user_id
    except Exception as e:
        print(f"Error getting Jellyfin auth: {e}")
        return None, None, None

def get_jellyfin_client(server_url, username, password):
    """Create and authenticate a Jellyfin client."""
    try:
        client = JellyfinClient()
        client.config.app('GenreLinker', '1.0.0', 'auto_genre_script', 'unique_id_001')
        client.config.data["auth.ssl"] = True
        client.auth.connect_to_address(server_url)
        client.auth.login(server_url, username, password)
        return client
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return None

def get_all_jellyfin_items(auth_token, user_id, server_url):
    """Get all movies and TV shows from Jellyfin with their genres."""
    try:
        headers = {
            'X-Emby-Token': auth_token,
            'Accept': 'application/json'
        }
        
        # Get movies
        movie_params = {
            'IncludeItemTypes': 'Movie',
            'Recursive': 'true',
            'Fields': 'Genres,ProductionYear,Path',
            'Limit': 1000
        }
        
        movie_response = requests.get(f'{server_url}/Users/{user_id}/Items', 
                                    headers=headers, params=movie_params)
        
        # Get TV series
        series_params = {
            'IncludeItemTypes': 'Series',
            'Recursive': 'true', 
            'Fields': 'Genres,ProductionYear,Path',
            'Limit': 1000
        }
        
        series_response = requests.get(f'{server_url}/Users/{user_id}/Items',
                                     headers=headers, params=series_params)
        
        items = []
        if movie_response.status_code == 200:
            movies = movie_response.json().get('Items', [])
            items.extend(movies)
            print(f"Found {len(movies)} movies in Jellyfin")
        
        if series_response.status_code == 200:
            series = series_response.json().get('Items', [])
            items.extend(series)
            print(f"Found {len(series)} TV series in Jellyfin")
        
        return items
        
    except Exception as e:
        print(f"Error getting Jellyfin items: {e}")
        return []

def clear_symlinks_in_directory(directory_path):
    """Remove all symlinks in a directory and its subdirectories."""
    if not os.path.exists(directory_path):
        print(f"Directory {directory_path} does not exist, skipping clearing")
        return 0, 0
    
    print(f"\nClearing existing symlinks in: {directory_path}")
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
    
    print(f"\nClearing summary for {os.path.basename(directory_path)}:")
    print(f"  Total symlinks found: {total_symlinks}")
    print(f"  Symlinks removed: {removed_symlinks}")
    
    return total_symlinks, removed_symlinks

def normalize_path(path):
    """Normalize path for comparison."""
    if not path:
        return ""
    # Remove common prefixes and normalize
    path = path.replace('\\', '/')
    path = re.sub(r'^[A-Z]:', '', path)  # Remove Windows drive letters
    return path.lower().strip('/')

def find_matching_jellyfin_item(local_path, jellyfin_items, is_movie=True):
    """Find matching Jellyfin item for a local file/folder."""
    local_name = Path(local_path).name.lower()
    
    # Extract year from folder name if present
    year_match = re.search(r'\((\d{4})\)', local_name)
    local_year = year_match.group(1) if year_match else None
    
    # Clean up the name for comparison
    clean_local_name = re.sub(r'\s*\(\d{4}\).*', '', local_name).strip()
    clean_local_name = re.sub(r'[^\w\s]', '', clean_local_name)
    
    best_match = None
    best_score = 0
    
    for item in jellyfin_items:
        item_type = item.get('Type', '')
        if is_movie and item_type != 'Movie':
            continue
        if not is_movie and item_type != 'Series':
            continue
            
        item_name = item.get('Name', '').lower()
        item_year = str(item.get('ProductionYear', '')) if item.get('ProductionYear') else None
        
        # Clean up Jellyfin name
        clean_item_name = re.sub(r'[^\w\s]', '', item_name)
        
        # Calculate similarity score
        score = 0
        
        # Exact name match
        if clean_local_name == clean_item_name:
            score += 100
        # Partial name match
        elif clean_local_name in clean_item_name or clean_item_name in clean_local_name:
            score += 50
        # Word overlap
        else:
            local_words = set(clean_local_name.split())
            item_words = set(clean_item_name.split())
            if local_words and item_words:
                overlap = len(local_words.intersection(item_words))
                score += (overlap / max(len(local_words), len(item_words))) * 30
        
        # Year bonus
        if local_year and item_year and local_year == item_year:
            score += 20
        
        if score > best_score and score > 40:  # Minimum threshold
            best_score = score
            best_match = item
    
    return best_match

def create_symlink(source_path, genre_path, item_name, container_target_path, genres_dir_container):
    """Create a relative symlink in the genre folder pointing to container target path."""
    try:
        # Create symlink path
        genre_abs = Path(genre_path).resolve()
        symlink_path = genre_abs / item_name
        
        # Calculate relative path within container filesystem
        # From: /media/Genres/Action/ (genre folder in container)
        # To: /media/Movies/MovieName (target in container)
        genre_name = os.path.basename(genre_path)
        container_genre_path = os.path.join(genres_dir_container, genre_name)
        relative_target = os.path.relpath(container_target_path, container_genre_path)
        
        # Always remove existing symlink or file if it exists
        if symlink_path.is_symlink():
            try:
                symlink_path.unlink()
            except OSError:
                pass  # Already removed or doesn't exist
        elif symlink_path.exists():
            # Regular file/directory exists with same name - skip to avoid data loss
            print(f"    Skipping {item_name} - regular file/directory already exists")
            return False
        
        # Create the symlink with relative container path
        symlink_path.symlink_to(relative_target)
        return True
        
    except Exception as e:
        print(f"    Error creating symlink: {e}")
        return False

def get_jellyfin_libraries(auth_token, server_url):
    """Get all existing Jellyfin libraries."""
    try:
        headers = {
            'X-Emby-Token': auth_token,
            'Accept': 'application/json'
        }
        
        response = requests.get(f'{server_url}/Library/VirtualFolders', headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get libraries. Status code: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Error getting Jellyfin libraries: {e}")
        return []

def create_jellyfin_library(auth_token, server_url, library_name, collection_type, paths):
    """Create a new Jellyfin library."""
    try:
        headers = {
            'X-Emby-Token': auth_token,
            'Accept': 'application/json'
        }
        
        if not paths:
            print(f"    ✗ No paths provided for library {library_name}")
            return False
        
        # Build query string with multiple paths parameters
        query_params = []
        query_params.append(f"name={requests.utils.quote(library_name)}")
        query_params.append(f"collectionType={collection_type}")
        query_params.append("refreshLibrary=false")
        
        # Add each path as a separate paths parameter
        for path in paths:
            query_params.append(f"paths={requests.utils.quote(path)}")
        
        url = f"{server_url}/Library/VirtualFolders?{'&'.join(query_params)}"
        
        print(f"    Debug: Creating library with URL: {url}")
        
        response = requests.post(url, headers=headers)
        
        if response.status_code in [200, 204]:
            print(f"    ✓ Created library: {library_name}")
            print(f"      Paths: {', '.join(paths)}")
            return True
        else:
            print(f"    ✗ Failed to create library {library_name}. Status: {response.status_code}")
            if response.text:
                print(f"      Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"    ✗ Error creating library {library_name}: {e}")
        return False

def add_path_to_jellyfin_library(auth_token, server_url, library_name, path):
    """Add a path to an existing Jellyfin library."""
    try:
        headers = {
            'X-Emby-Token': auth_token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        data = {
            'Name': library_name,
            'PathInfo': {
                'Path': path
            }
        }
        
        response = requests.post(f'{server_url}/Library/VirtualFolders/Paths', 
                               headers=headers, json=data)
        
        if response.status_code in [200, 204]:
            print(f"    ✓ Added path to library {library_name}: {path}")
            return True
        else:
            print(f"    ✗ Failed to add path to library {library_name}. Status: {response.status_code}")
            if response.text:
                print(f"      Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"    ✗ Error adding path to library {library_name}: {e}")
        return False

def update_jellyfin_library_path(auth_token, server_url, library_name, path):
    """Update a path in an existing Jellyfin library."""
    try:
        headers = {
            'X-Emby-Token': auth_token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        data = {
            'Name': library_name,
            'PathInfo': {
                'Path': path
            }
        }
        
        response = requests.post(f'{server_url}/Library/VirtualFolders/Paths/Update', 
                               headers=headers, json=data)
        
        if response.status_code in [200, 204]:
            print(f"    ✓ Updated library path: {library_name} -> {path}")
            return True
        else:
            print(f"    ✗ Failed to update library {library_name}. Status: {response.status_code}")
            if response.text:
                print(f"      Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"    ✗ Error updating library {library_name}: {e}")
        return False

def refresh_jellyfin_libraries(auth_token, server_url):
    """Refresh all Jellyfin libraries."""
    try:
        headers = {
            'X-Emby-Token': auth_token,
            'Accept': 'application/json'
        }
        
        response = requests.post(f'{server_url}/Library/Refresh', headers=headers)
        
        if response.status_code in [200, 204]:
            print("    ✓ Library refresh initiated")
            return True
        else:
            print(f"    ✗ Failed to refresh libraries. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"    ✗ Error refreshing libraries: {e}")
        return False

def ensure_genre_folders(genres_dir, jellyfin_items):
    """Ensure all necessary genre folders exist in the given directory."""
    print(f"\nEnsuring genre folders exist in: {genres_dir}")
    
    # Create base genres directory if it doesn't exist
    Path(genres_dir).mkdir(parents=True, exist_ok=True)
    
    # Collect all unique genres from Jellyfin items
    all_genres = set()
    for item in jellyfin_items:
        genres = item.get('Genres', [])
        all_genres.update(genres)
    
    # Create genre folders
    created_count = 0
    for genre in sorted(all_genres):
        if genre:  # Skip empty genres
            # Clean up genre name for folder creation
            clean_genre = re.sub(r'[<>:"/\\|?*]', '_', genre).strip()
            genre_path = Path(genres_dir) / clean_genre
            
            if not genre_path.exists():
                genre_path.mkdir(parents=True, exist_ok=True)
                print(f"  Created: {clean_genre}")
                created_count += 1
    
    print(f"  Created {created_count} new genre folders")
    return len(all_genres)

def manage_jellyfin_genre_libraries(auth_token, server_url, genres_dir_host, 
                                   genres_dir_container, jellyfin_items, include_shows):
    """Manage Jellyfin libraries for genre folders."""
    print("\n" + "=" * 60)
    print("MANAGING JELLYFIN GENRE LIBRARIES")
    print("=" * 60)
    
    # Determine collection type
    collection_type = "mixed" if include_shows else "movies"
    print(f"Collection type: {collection_type}")
    
    # Get existing libraries
    print("\nGetting existing Jellyfin libraries...")
    existing_libraries = get_jellyfin_libraries(auth_token, server_url)
    existing_library_names = {lib.get('Name', '') for lib in existing_libraries}
    
    print(f"Found {len(existing_libraries)} existing libraries")
    
    # Collect all unique genres from Jellyfin items
    all_genres = set()
    for item in jellyfin_items:
        genres = item.get('Genres', [])
        all_genres.update(genres)
    
    # Process each genre
    created_count = 0
    updated_count = 0
    
    for genre in sorted(all_genres):
        if not genre:  # Skip empty genres
            continue
            
        # Clean up genre name for library creation
        clean_genre = re.sub(r'[<>:"/\\|?*]', '_', genre).strip()
        library_name = clean_genre
        
        # Build host path for existence checking
        genre_path_host = f"{genres_dir_host}/{clean_genre}"
        
        # Build container path for Jellyfin library creation
        genre_path_container = f"{genres_dir_container}/{clean_genre}"
        
        # Check if path exists on host and build container paths list
        paths = []
        if os.path.exists(genre_path_host):
            paths.append(genre_path_container)
        
        if not paths:
            print(f"  Skipping {library_name} - no genre folders exist")
            continue
        
        print(f"\nProcessing genre library: {library_name}")
        print(f"  Paths: {', '.join(paths)}")
        
        if library_name in existing_library_names:
            print(f"  Library exists, updating paths...")
            # Update existing library paths
            success = True
            for path in paths:
                if not update_jellyfin_library_path(auth_token, server_url, library_name, path):
                    success = False
            if success:
                updated_count += 1
        else:
            print(f"  Creating new library...")
            # Create new library
            if create_jellyfin_library(auth_token, server_url, library_name, collection_type, paths):
                created_count += 1
    
    print(f"\nLibrary management summary:")
    print(f"  Libraries created: {created_count}")
    print(f"  Libraries updated: {updated_count}")
    
    # Refresh libraries
    print(f"\nRefreshing Jellyfin libraries...")
    refresh_jellyfin_libraries(auth_token, server_url)
    
    return created_count, updated_count

def process_media_folder(media_path, genre_base_path, jellyfin_items, container_media_path, genres_dir_container, is_movie=True):
    """Process all items in a media folder."""
    media_type = "movies" if is_movie else "TV shows"
    print(f"\nProcessing {media_type} in {media_path}")
    print(f"Creating symlinks in: {genre_base_path}")
    print("=" * 70)
    
    if not os.path.exists(media_path):
        print(f"Path {media_path} does not exist, skipping!")
        return 0, 0
    
    processed = 0
    linked = 0
    
    for item_name in os.listdir(media_path):
        item_path = os.path.join(media_path, item_name)
        
        # Skip files, only process directories
        if not os.path.isdir(item_path):
            continue
        
        print(f"\nProcessing: {item_name}")
        
        # Find matching Jellyfin item
        jellyfin_item = find_matching_jellyfin_item(item_path, jellyfin_items, is_movie)
        
        if not jellyfin_item:
            print(f"  No matching Jellyfin item found")
            processed += 1
            continue
        
        # Get genres (limit to top 5)
        genres = jellyfin_item.get('Genres', [])[:5]
        
        if not genres:
            print(f"  No genres found for {jellyfin_item.get('Name')}")
            processed += 1
            continue
        
        print(f"  Found: {jellyfin_item.get('Name')} ({jellyfin_item.get('ProductionYear', 'Unknown')})")
        print(f"  Genres: {', '.join(genres)}")
        
        # Create symlinks for each genre
        item_linked = 0
        for genre in genres:
            # Clean up genre name
            clean_genre = re.sub(r'[<>:"/\\|?*]', '_', genre).strip()
            genre_folder = os.path.join(genre_base_path, clean_genre)
            
            if not os.path.exists(genre_folder):
                print(f"    Genre folder {clean_genre} doesn't exist, skipping")
                continue
            
            # Build container path for this item (for Docker container compatibility)
            container_item_path = os.path.join(container_media_path, item_name)
            
            link_result = create_symlink(item_path, genre_folder, item_name, container_item_path, genres_dir_container)
            if link_result:
                print(f"    ✓ Linked to {clean_genre}")
                item_linked += 1
            else:
                print(f"    - Already linked to {clean_genre}")
        
        if item_linked > 0:
            linked += 1
        
        processed += 1
    
    print(f"\n{media_type.title()} summary for {os.path.basename(media_path)}:")
    print(f"  Processed: {processed}")
    print(f"  Items with new links: {linked}")
    
    return processed, linked

def main():
    """Main function."""
    print("Jellyfin Genre Symlink Creator")
    print("=" * 60)
    
    # Load configuration
    config = load_config()
    print(f"Configuration loaded from .env")
    
    # Extract configuration
    server_url = config.get('SERVER_URL')
    username = config.get('USERNAME')
    password = config.get('PASSWORD')
    include_shows = config.get('INCLUDE_SHOWS', True)
    
    # Parse path mappings (host:container)
    movies_dir_host, movies_dir_container = parse_path_mapping(config.get('MOVIES_DIR', ''))
    shows_dir_host, shows_dir_container = parse_path_mapping(config.get('SHOWS_DIR', ''))
    genres_dir_host, genres_dir_container = parse_path_mapping(config.get('GENRES_DIR', ''))
    
    # Use host paths for local file operations
    movies_dir = movies_dir_host
    shows_dir = shows_dir_host
    genres_dir = genres_dir_host
    
    # Validate required configuration
    required_config = ['SERVER_URL', 'USERNAME', 'PASSWORD', 'MOVIES_DIR', 'GENRES_DIR']
    missing_config = [key for key in required_config if not config.get(key)]
    
    if missing_config:
        print(f"Error: Missing required configuration: {', '.join(missing_config)}")
        sys.exit(1)
    
    print("Processing configured directories")
    
    print(f"Include TV shows: {include_shows}")
    print(f"Movies directory: {movies_dir}")
    if include_shows:
        print(f"TV shows directory: {shows_dir}")
    print(f"Genre directory: {genres_dir}")
    
    # Get Jellyfin authentication
    print("\nAuthenticating with Jellyfin...")
    client, auth_token, user_id = get_jellyfin_client_and_auth(server_url, username, password)
    
    if not client or not auth_token:
        print("Failed to authenticate with Jellyfin!")
        sys.exit(1)
    
    print(f"Successfully authenticated. User ID: {user_id}")
    
    # Get all Jellyfin items
    print("\nFetching all items from Jellyfin...")
    jellyfin_items = get_all_jellyfin_items(auth_token, user_id, server_url)
    
    if not jellyfin_items:
        print("No items found in Jellyfin!")
        sys.exit(1)
    
    print(f"Found {len(jellyfin_items)} total items in Jellyfin")
    
    # Clear existing symlinks first
    print("\n" + "=" * 60)
    print("CLEARING EXISTING SYMLINKS")
    print("=" * 60)
    
    total_cleared = 0
    if os.path.exists(genres_dir):
        found, removed = clear_symlinks_in_directory(genres_dir)
        total_cleared += removed
        print(f"\n✓ Cleared {removed} existing symlinks from genre folders")
    else:
        print(f"Genre directory {genres_dir} does not exist yet, nothing to clear")
    
    # Ensure genre folders exist
    print("\n" + "=" * 60)
    print("SETTING UP GENRE FOLDERS")
    print("=" * 60)
    
    genres_count = ensure_genre_folders(genres_dir, jellyfin_items)
    
    print(f"\nGenre folders setup:")
    print(f"  {genres_dir}: {genres_count} genres")
    
    # Process all directories
    print("\n" + "=" * 60)
    print("PROCESSING MEDIA DIRECTORIES")
    print("=" * 60)
    
    total_processed = 0
    total_linked = 0
    
    # Process movies
    if os.path.exists(movies_dir):
        processed, linked = process_media_folder(movies_dir, genres_dir, jellyfin_items, movies_dir_container, genres_dir_container, is_movie=True)
        total_processed += processed
        total_linked += linked
    else:
        print(f"\nMovies path {movies_dir} does not exist, skipping")
    
    # Process TV shows if enabled
    if include_shows:
        if shows_dir and os.path.exists(shows_dir):
            processed, linked = process_media_folder(shows_dir, genres_dir, jellyfin_items, shows_dir_container, genres_dir_container, is_movie=False)
            total_processed += processed
            total_linked += linked
        elif shows_dir:
            print(f"\nTV shows path {shows_dir} does not exist, skipping")
        else:
            print(f"\nTV shows directory not configured, skipping")
    else:
        print("\nTV shows processing disabled in configuration")
    
    # Manage Jellyfin genre libraries
    print("\n" + "=" * 60)
    print("JELLYFIN LIBRARY MANAGEMENT")
    print("=" * 60)
    
    try:
        libraries_created, libraries_updated = manage_jellyfin_genre_libraries(
            auth_token, server_url, genres_dir_host, 
            genres_dir_container, jellyfin_items, include_shows
        )
        
        print(f"\n✓ Jellyfin library management complete!")
        print(f"  Libraries created: {libraries_created}")
        print(f"  Libraries updated: {libraries_updated}")
        
    except Exception as e:
        print(f"\n✗ Error managing Jellyfin libraries: {e}")
        print("Symlinks were created successfully, but library management failed.")
    
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Existing symlinks cleared: {total_cleared}")
    print(f"Total items processed: {total_processed}")
    print(f"Total items with new links: {total_linked}")
    print(f"\n✓ Genre symlink creation complete!")
    print(f"Check the following directory for your organized media links:")
    print(f"  - {genres_dir}")
    print(f"\n✓ Check your Jellyfin server for the new genre libraries!")

if __name__ == "__main__":
    main()

