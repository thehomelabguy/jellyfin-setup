# Genre Symlink Creator - Multi-Directory Version

This script creates symlinks for movies and TV shows organized by genre across multiple directories.

## Features

- **Multi-directory support**: Process movies and shows from multiple source directories
- **Flexible genre folders**: Create genre folders in multiple target directories
- **Configuration-driven**: All settings managed via a single config file
- **TV shows optional**: Can enable/disable TV show processing
- **Automatic genre folder creation**: Creates all necessary genre folders automatically
- **Jellyfin library management**: Automatically creates and manages Jellyfin libraries for each genre
- **Smart library updates**: Updates existing libraries or creates new ones as needed

## Configuration

Edit `config.env` to configure your setup:

```bash
# Jellyfin Server Configuration
SERVER_URL=https://watch.pensotti.net
USERNAME=your_username
PASSWORD=your_password

# Media Directory Configuration
INCLUDE_SHOWS=true

# Movies Directories
MOVIES_DIR_1=/mnt/media_a/Radarr/Movies
MOVIES_DIR_2=/mnt/media_b/Radarr/Movies

# TV Shows Directories (only used if INCLUDE_SHOWS=true)
SHOWS_DIR_1=/mnt/media_a/Sonarr/tvshows
SHOWS_DIR_2=/mnt/media_b/Sonarr/tvshows

# Genre Folders Base Paths (will be created if they don't exist)
GENRES_DIR_1=/mnt/media_a/Genres
GENRES_DIR_2=/mnt/media_b/Genres
```

## How It Works

1. **Movies Processing**:
   - Movies from `MOVIES_DIR_1` → Symlinks in `GENRES_DIR_1`
   - Movies from `MOVIES_DIR_2` → Symlinks in `GENRES_DIR_2`

2. **TV Shows Processing** (if `INCLUDE_SHOWS=true`):
   - Shows from `SHOWS_DIR_1` → Symlinks in `GENRES_DIR_1`
   - Shows from `SHOWS_DIR_2` → Symlinks in `GENRES_DIR_2`

3. **Genre Folder Creation**:
   - Automatically creates all necessary genre folders in both `GENRES_DIR_1` and `GENRES_DIR_2`
   - Based on genres found in your Jellyfin library

4. **Jellyfin Library Management**:
   - Automatically creates Jellyfin libraries for each genre
   - Each genre library includes paths from both genre directories
   - Updates existing libraries if they already exist
   - Uses `mixed` collection type if shows are included, `movies` if not
   - Refreshes all libraries after setup

## Usage

```bash
# Run the multi-directory version
./create_genre_symlinks_multi.py

# Or run with Python
python3 create_genre_symlinks_multi.py
```

## Requirements

- Python 3.6+
- `jellyfin_apiclient_python` package
- `requests` package
- Access to Jellyfin server
- Write permissions to genre directories

## Directory Structure Example

After running, you'll have:

```
/mnt/media_a/
├── Radarr/Movies/           # Source movies
├── Sonarr/tvshows/          # Source TV shows
└── Genres/                  # Genre symlinks for media_a content
    ├── Action/
    ├── Comedy/
    └── ...

/mnt/media_b/
├── Radarr/Movies/           # Source movies
├── Sonarr/tvshows/          # Source TV shows  
└── Genres/                  # Genre symlinks for media_b content
    ├── Action/
    ├── Comedy/
    └── ...
```

## Benefits

- **Organized by storage**: Each storage location has its own genre organization
- **Relative symlinks**: Symlinks work even if mount points change
- **Jellyfin integration**: Uses your existing Jellyfin library for genre data
- **Flexible configuration**: Easy to add/remove directories or disable shows

## Files in This Directory

- `create_genre_symlinks_multi.py` - Main script for creating genre symlinks
- `config.env` - Configuration file with all settings
- `requirements.txt` - Python dependencies
- `README.md` - This documentation

## Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your settings in `config.env`

3. Run the script:
   ```bash
   ./create_genre_symlinks_multi.py
   ```
