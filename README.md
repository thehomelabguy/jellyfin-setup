# 🎬 Ultimate Media Server Setup

> **A comprehensive guide to setting up a complete media server infrastructure with Docker, VPN protection, and automated download clients.**

---

<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/selfhst/icons/png/docker.png" width="32" height="32"> Docker Installation</h2>
</summary>

```bash
# Update system
sudo apt update

# Install prerequisites
sudo apt install apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
sudo docker run hello-world
```

</details>


<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/dockge.png" width="32" height="32"> Dockge Setup</h2>
</summary>

### Installation
```bash
# Create directories that store your stacks and stores Dockge's stack
cd /
sudo mkdir -p /opt/stacks /opt/dockge
sudo chown -R $USER:$USER /opt
cd /opt/dockge

# Download the compose.yaml
curl https://raw.githubusercontent.com/louislam/dockge/master/compose.yaml --output compose.yaml

# Start the server
sudo docker compose up -d

# If you are using docker-compose V1 or Podman
# docker-compose up -d
```

**Access:** [`http://localhost:5001`](http://localhost:5001)

</details>


<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/nordvpn.png" width="32" height="32"> NordVPN + Gluetun Setup</h2>
</summary>

### Install NordVPN Client

```bash
sh <(curl -sSf https://downloads.nordcdn.com/apps/linux/install.sh)
sudo apt install wireguard net-tools
```

### Authentication Setup

### 🖥️ Authentication Setup

#### For Non-GUI Users (Headless Servers)

1. **Access Your NordVPN Account**
   - Navigate to [Nord Account Dashboard](https://my.nordaccount.com/?nv_tri=TC_7789917667737013_1756501610170&nv_trs=1756501610171_1756502282877_1_147&_gl=1*749t8t*FPAU*MTUxMjQ1MDUzMy4xNzU2NTAxNjE0*_ga*NzU1MTQyMTYwLjE3NTY1MDE2MTA.*_ga_LEXMJ1N516*czE3NTY1MDE2MTAkbzEkZzEkdDE3NTY1MDIyODIkajYwJGwwJGgw&_ga=2.208263835.861224087.1756501721-755142160.1756501610)

2. **Locate NordVPN Service**
   - Find NordVPN under the Services menu
   
   ![NordVPN Services Menu](assets/image1.png)

3. **Generate Access Token**
   - Locate the "Access token" tab
   - Click on "Generate new token"
   
   ![NordVPN Token Generation](assets/image2.png)

4. **Login with Token**
   - Copy the generated token and run:
   ```bash
   # For headless servers
   nordvpn login --token [YOUR_TOKEN]
   
   # For GUI systems
   nordvpn login
   ```
3. **Configure permissions:**
   ```bash
   sudo usermod -aG nordvpn $USER
   nordvpn connect
   ```

---

### Extract VPN Configuration for Gluetun

```bash
# Get private key
sudo wg show nordlynx private-key

# Get IP address
ifconfig nordlynx
```

## Gluetun

Copy the private key and IP address (e.g., `10.5.0.2/16`) to your Gluetun Docker configuration.

```properties
# .env
TZ=America/New_York
VPN_SERVICE_PROVIDER=nordvpn
VPN_TYPE=wireguard
WIREGUARD_ADDRESSES=[YOUR_INET_IP]
WIREGUARD_PRIVATE_KEY=[YOUR_PRIVATE_KEY]
```


   
   ```yaml
  networks:
    servarr-network:
      name: servarr-network
      ipam:
        config:
          - subnet: 172.38.0.0/24

  services:
    gluetun:
      image: qmcgaw/gluetun
      container_name: gluetun
      hostname: gluetun
      cap_add:
        - NET_ADMIN
      devices:
        - /dev/net/tun:/dev/net/tun
      networks:
        servarr-network:
          ipv4_address: 172.38.0.2
      ports:
        - 8080:8080 # qbittorrent
        - 6881:6881 # qbittorrent listen
        - 6881:6881/udp # qbittorrent listen
        - 9696:9696 # prowlarr
      volumes:
        - ./gluetun:/gluetun
      environment:
        - VPN_SERVICE_PROVIDER=${VPN_SERVICE_PROVIDER}
        - VPN_TYPE=${VPN_TYPE}
        - WIREGUARD_PRIVATE_KEY=${WIREGUARD_PRIVATE_KEY}
        - WIREGUARD_ADDRESSES=${WIREGUARD_ADDRESSES}
        - TZ=${TZ}
        - UPDATER_PERIOD=24h
      healthcheck:
        test: ping -c 1 www.google.com || exit 1
        interval: 20s
        timeout: 10s
        retries: 5
      restart: unless-stopped
   ```

</details>


<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/qbittorrent.png" width="32" height="32"> Download Client Setup</h2>
</summary>

```yaml
qbittorrent:
    image: lscr.io/linuxserver/qbittorrent
    container_name: qbittorrent
    network_mode: service:gluetun
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
      - WEBUI_PORT=8080
    volumes:
      - ./qbittorrent:/config
      - ${DOWNLOADS_DIRECTORY}:/downloads
    restart: unless-stopped
    depends_on:
      gluetun:
        condition: service_healthy
```

```properties
PUID=1000
PGID=1000

DOWNLOADS_DIRECTORY=/mnt/media/Downloads
```

### QBittorrent Configuration

**Access:** `127.0.0.1:8085` | **NZBget:** `127.0.0.1:6789`

#### Initial Login

1. Find temporary password in Dockge logs: `admin / [generated_password]`
2. Change username/password in settings after login

---

### Recommended Torrent Trackers

<details>
<summary>
🔗 <strong>Click to expand tracker list</strong> (Copy and paste into QBittorrent settings) [Source](https://newtrackon.com/list)
</summary>

```
udp://tracker.opentrackr.org:1337/announce
udp://p4p.arenabg.com:1337/announce
udp://d40969.acod.regrucolo.ru:6969/announce
udp://evan.im:6969/announce
https://tracker.jdx3.org:443/announce
udp://retracker.lanta.me:2710/announce
http://lucke.fenesisu.moe:6969/announce
http://tracker.renfei.net:8080/announce
https://tracker.expli.top:443/announce
https://tr.nyacat.pw:443/announce
udp://tracker.ducks.party:1984/announce
udp://extracker.dahrkael.net:6969/announce
http://ipv4.rer.lol:2710/announce
udp://tracker.tvunderground.org.ru:3218/announce
udp://tracker.kmzs123.cn:17272/announce
https://tracker.alaskantf.com:443/announce
udp://tracker.dler.com:6969/announce
http://bt.okmp3.ru:2710/announce
udp://tracker.torrent.eu.org:451/announce
http://tracker.mywaifu.best:6969/announce
udp://bandito.byterunner.io:6969/announce
udp://tracker.plx.im:6969/announce
udp://open.stealth.si:80/announce
https://tracker.moeblog.cn:443/announce
https://tracker.yemekyedim.com:443/announce
udp://tracker.fnix.net:6969/announce
udp://martin-gebhardt.eu:25/announce
udp://tracker.valete.tf:9999/announce
http://tracker.bt4g.com:2095/announce
udp://retracker01-msk-virt.corbina.net:80/announce
udp://tracker.srv00.com:6969/announce
udp://open.demonii.com:1337/announce
udp://www.torrent.eu.org:451/announce
udp://bt.bontal.net:6969/announce
udp://tracker.torrust-demo.com:6969/announce
http://open.trackerlist.xyz:80/announce
udp://tracker.gigantino.net:6969/announce
http://torrent.hificode.in:6969/announce
udp://tracker.therarbg.to:6969/announce
udp://opentracker.io:6969/announce
udp://1c.premierzal.ru:6969/announce
http://0123456789nonexistent.com:80/announce
udp://tracker.cloudbase.store:1333/announce
http://shubt.net:2710/announce
udp://tracker.zupix.online:1333/announce
udp://tracker.rescuecrew7.com:1337/announce
udp://tracker.startwork.cv:1337/announce
udp://tracker.skillindia.site:6969/announce
udp://tracker.hifitechindia.com:6969/announce
udp://tracker.bitcoinindia.space:6969/announce
udp://ttk2.nbaonlineservice.com:6969/announce
https://tracker.zhuqiy.top:443/announce
https://2.tracker.eu.org:443/announce
udp://tracker.hifimarket.in:2710/announce
https://4.tracker.eu.org:443/announce
https://3.tracker.eu.org:443/announce
udp://tr4ck3r.duckdns.org:6969/announce
udp://6ahddutb1ucc3cp.ru:6969/announce
https://shahidrazi.online:443/announce

```

</details>

**Add to QBittorrent:** Settings → BitTorrent → "Automatically add these trackers to new downloads"

</details>

<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/prowlarr.png" width="24" height="24"> <img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/radarr.png" width="24" height="24"> <img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/sonarr.png" width="24" height="24"> Setting up the Arrrrs ☠️</h2>
</summary>

Setup for **Prowlarr**, **Radarr**, and **Sonarr**.

2. Deploy Radarr and Sonarr
```yaml
  prowlarr:
    image: lscr.io/linuxserver/prowlarr:latest
    container_name: prowlarr
    network_mode: service:gluetun
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    volumes:
      - ./prowlarr:/config
      - ./prowlarr/backup:/data/backup
    restart: unless-stopped
    depends_on:
      gluetun:
        condition: service_healthy
  flaresolverr:
    container_name: flaresolverr
    image: ghcr.io/flaresolverr/flaresolverr:latest
    network_mode: service:gluetun
    environment:
      - LOG_LEVEL=info
    restart: unless-stopped
    depends_on:
      gluetun:
        condition: service_healthy
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    container_name: sonarr
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    volumes:
      - ./sonarr:/config
      - ${SONARR_BACKUP_DIR}:/data/Backup
      - ${SHOWS_DIRECTORY}:/data/tvshows
      - ${DOWNLOADS_DIRECTORY}:/downloads
    ports:
      - 8989:8989
    restart: unless-stopped
    networks:
      servarr-network:
        ipv4_address: 172.38.0.3
  radarr:
    image: lscr.io/linuxserver/radarr:latest
    container_name: radarr
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    volumes:
      - ./radarr:/config
      - ${MOVIES_DIRECTORY}:/data/movies
      - ${RADARR_BACKUP_DIR}:/data/backup
      - ${DOWNLOADS_DIRECTORY}:/downloads
    ports:
      - 7878:7878
    restart: unless-stopped
    networks:
      servarr-network:
        ipv4_address: 172.38.0.4
```

```properties 
MOVIES_DIRECTORY=/mnt/media/Radarr/Movies
RADARR_BACKUP_DIR=/mnt/media/Radarr/Backup
SHOWS_DIRECTORY=/mnt/media/Sonarr/Shows
SONARR_BACKUP_DIR=/mnt/media/Sonarr/Backup
```

### 2. Set Permissions

```bash
sudo chown -R $USER:$USER /mnt/media
```

### 3. Prowlarr Configuration

**Access:** [`http://localhost:9697`](http://localhost:9697)

1. **Settings** → **Apps** → Connect Radarr & Sonarr (use API keys)
2. **Settings** → **Apps** → Connect QBittorrent 
3. **Indexers** → Add public indexers (1337x, RARBG, TPB, YTS, EZTV)
4. **Optional:** Configure FlareSolverr for Cloudflare bypass

### 4. Radarr Configuration

**Access:** [http://localhost:7878](http://localhost:7878)

1. **Settings** → **Media Management** → Add Root Folder: `/data/movies`
2. **Settings** → **Download Clients** → Add QBittorrent (category: `movies`)
3. **Settings** → **Profiles** → Configure quality preferences

### 5. Sonarr Configuration

**Access:** [http://localhost:8989](http://localhost:8989)

1. **Settings** → **Media Management** → Add Root Folder: `/data/tvshows`
2. **Settings** → **Media Management** → Enable folder management options
3. **Settings** → **Download Clients** → Add QBittorrent (category: `tv`)
4. **Settings** → **Profiles** → Configure quality preferences

</details>


<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/jellyfin.png" width="32" height="32"> Jellyfin Media Server</h2>
</summary>



### Docker Compose

```yaml
services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    user: ${PUID}:${PGID}
    volumes:
      - ./jellyfin:/config
      - ./jellyfin/cache:/cache
      - type: bind
        source: ${MOVIES_DIRECTORY}
        target: /media/movies
      - type: bind
        source: ${SHOWS_DIRECTORY}
        target: /media/shows
      - type: bind
        source: ${GENRES_DIRECTORY}
        target: /media/genres
    restart: unless-stopped
    extra_hosts:
      - host.docker.internal:host-gateway
    networks:
      - jellyfin-network
    ports:
      - 8096:8096
networks:
  jellyfin-network:
    driver: bridge
```

## Jellyfin Setup

**Access:** [`http://localhost:8096`](http://localhost:8096)

1. **Language Selection** & **Admin Account** setup
2. **Add Media Libraries:**
   - Movies: `/media/movies`
   - TV Shows: `/media/shows`

Once you've setup and logged into Jellyfin, go back to Dockge and add these binds to Jellyfin volumes.

```yaml
      - /opt/jellyfin-setup/images/favicon.png:/jellyfin/jellyfin-web/favicon.png
      - /opt/jellyfin-setup/images/bc8d51405ec040305a87.ico:/jellyfin/jellyfin-web/bc8d51405ec040305a87.ico
      - /opt/jellyfin-setup/images/banner-dark.png:/jellyfin/jellyfin-web/assets/img/banner-dark.png
      - /opt/jellyfin-setup/images/banner-light.png:/jellyfin/jellyfin-web/assets/img/banner-light.png
      - /opt/jellyfin-setup/images/touchicon.png:/jellyfin/jellyfin-web/touchicon.png
      - /opt/jellyfin-setup/images/touchicon72.png:/jellyfin/jellyfin-web/touchicon72.png
      - /opt/jellyfin-setup/images/touchicon114.png:/jellyfin/jellyfin-web/touchicon114.png
      - /opt/jellyfin-setup/images/touchicon144.png:/jellyfin/jellyfin-web/touchicon144.png
      - /opt/jellyfin-setup/images/touchicon512.png:/jellyfin/jellyfin-web/touchicon512.png
      - /opt/jellyfin-setup/code/index.html:/jellyfin/jellyfin-web/index.html
      - /opt/jellyfin-setup/code/main.jellyfin.bundle.js:/jellyfin/jellyfin-web/main.jellyfin.bundle.js
      - /opt/jellyfin-setup/code/main.jellyfin.7d6eaeb032d03eb0ae47.css:/jellyfin/jellyfin-web/main.jellyfin.7d6eaeb032d03eb0ae47.css
      - /opt/jellyfin-setup/code/home-html.8ce38bc7d6dc073656d4.chunk.js:/jellyfin/jellyfin-web/home-html.8ce38bc7d6dc073656d4.chunk.js
      - /opt/jellyfin-setup/code/73233.d08d0c3a593dcbf1c7c7.chunk.js:/jellyfin/jellyfin-web/73233.d08d0c3a593dcbf1c7c7.chunk.js
```

Restart Jellyfin.

## Genres Setup (Linux Only)

```bash
# Download Python and venv
sudo apt update && sudo apt install python3 python3-pip python3-venv -y

# Navigate to auto-genre directory and setup virtual environment
cd /opt/jellyfin-setup/auto-genre
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Change Jellyfin Username and Password in .env file. 

```bash 
# /auto-genre/.env

USERNAME=root #change me
PASSWORD=password #change me
```

Run the create_genre_symlinks.py script.
```bash
./create_genre_symlinks.py
```

## Jellyfin Custom CSS

Go to Dashboard -> General -> Custom CSS code and add:

```css
@import url(https://cdn.jsdelivr.net/gh/apensotti/ZestyTheme@main/theme.css);
@import url('https://cdn.jsdelivr.net/gh/stpnwf/ZestyTheme@latest/colorschemes/gray.css');

.adminDrawerLogo img { content: url(https://imagedelivery.net/ZYTNwtC8cUrRhA9tP_rjhg/9c952c1e-f37a-445e-ef74-609621ae6600/public) !important; } imgLogoIcon { content: url(https://imagedelivery.net/ZYTNwtC8cUrRhA9tP_rjhg/9c952c1e-f37a-445e-ef74-609621ae6600/public) !important; } .pageTitleWithLogo { background-image: url(https://imagedelivery.net/ZYTNwtC8cUrRhA9tP_rjhg/9c952c1e-f37a-445e-ef74-609621ae6600/public) !important; }
```

Click ```F12``` and right click the page refresh button and click ```Empty Cache and Hard Reload```  

## Plugins

Go to Dashboard -> Catalog:

Install the following plugins:

``` 
AniDB
AniList
Artwork
Chapter Segments Provider
Fanart
OMDb
Open Subtitles
Playback Reporting
Reports
Session Cleaner
Studio Images
Subtitle Extract
TMDb
TMDb Boxsets
TVmaze
TheTVDB
Trakt
```

Now go to the setting icon next to ```Catalog``` and click ```+```

```
Repository Name: Merge Versions
Repository URL: https://raw.githubusercontent.com/danieladov/JellyfinPluginManifest/master/manifest.json
```

Go back to catalog and install ```Merge Versions```

Go to Dashboard and click ```Restart```, wait and refresh.

Finally go to Dashboard -> Scheduled Tasks run TMDb ```Scan library for new box sets```

</details>

<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/jellyseerr.png" width="32" height="32"> Jellyseerr Requests</h2>
</summary>

```yaml
services:
  jellyseerr:
    image: fallenbagel/jellyseerr:latest
    container_name: jellyseerr
    environment:
      - LOG_LEVEL=debug
      - TZ=America/New_York
      - PORT=5055
    ports:
      - 5055:5055
    volumes:
      - ./config:/app/config
    restart: unless-stopped
```

Setting up Jellyseer:
1. Choose Jellyfin
2. Add Jellyfin IP (Leave Base URL blank)
3. Input Jellyfin Username and Password
4. Click ```Sync Libraries``` and select ONLY ```Movies``` and ```Shows```
5. Radarr Setup:
   - Server Name: Radarr
   - Hostname or IP: radarr
   - Port: 7878
   - API Key: (from Radarr settings)
   - Base URL: (leave blank)
   - Quality Profile: (select preferred)
   - Root Folder: /data/movies
6. Sonarr Setup:
   - Server Name: Sonarr
   - Hostname or IP: sonarr
   - Port: 8989
   - API Key: (from Sonarr settings)
   - Base URL: (leave blank)
   - Quality Profile: (select preferred)
   - Root Folder: /data/tv

</details>

<details>
<summary>
<h2><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/nginx-proxy-manager.png" width="32" height="32"> Nginx Proxy Manager</h2>
</summary>

Nginx Proxy Manager is a simple, powerful tool for managing Nginx proxy hosts with a beautiful web interface. It allows you to easily set up SSL certificates, manage domains, and create proxy configurations without touching Nginx configuration files.

### Docker Compose

```yaml
services:
  nginx:
    image: jc21/nginx-proxy-manager:latest
    restart: unless-stopped
    ports:
      # These ports are in format <host-port>:<container-port>
      - 80:80 # Public HTTP Port
      - 443:443 # Public HTTPS Port
      - 81:81 # Admin Web Port
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
networks:
  jellyfin_jellyfin-network:
    external: true
  servarr_servarr-network:
    external: true
```

### Initial Setup

**Access:** [`http://localhost:81`](http://localhost:81)

**Default Login Credentials:**
- Email: `admin@example.com`
- Password: `changeme`

**Important:** Change these credentials immediately after first login!

### Configuration Steps

1. **Login** with default credentials
2. **Change Admin Credentials:**
   - Go to Users → Edit admin user
   - Update email and password
   - Save changes

3. **Add Proxy Hosts:**
   - Click "Proxy Hosts" → "Add Proxy Host"
   - Enter your domain name
   - Set destination IP and port (e.g., `jellyfin:8096`)
   - Enable "Block Common Exploits"
   - Enable "Websockets Support" if needed

4. **SSL Certificate Setup:**
   - Go to the "SSL" tab
   - Select "Request a new SSL Certificate"
   - Enter your email
   - Enable "Force SSL" and "HTTP/2 Support"
   - Click "Save"

### Common Proxy Configurations

**Jellyfin Media Server:**
- Domain: `jellyfin.yourdomain.com`
- Forward IP: `jellyfin` (container name)
- Forward Port: `8096`
- Enable Websockets Support

**Radarr:**
- Domain: `radarr.yourdomain.com` 
- Forward IP: `radarr`
- Forward Port: `7878`

**Sonarr:**
- Domain: `sonarr.yourdomain.com`
- Forward IP: `sonarr` 
- Forward Port: `8989`

**Jellyseerr:**
- Domain: `requests.yourdomain.com`
- Forward IP: `jellyseerr`
- Forward Port: `5055`

### Security Recommendations

1. **Access Lists:** Create access lists to restrict admin panel access
2. **Strong Passwords:** Use complex passwords for all accounts
3. **Regular Updates:** Keep Nginx Proxy Manager updated
4. **Firewall Rules:** Configure firewall to only allow necessary ports
5. **SSL Only:** Always force SSL for public-facing services

### Troubleshooting

**Common Issues:**
- **502 Bad Gateway:** Check if target service is running and accessible
- **SSL Certificate Fails:** Ensure domain points to your server's public IP
- **Can't Access Admin Panel:** Check if port 81 is accessible and not blocked by firewall

**Logs Location:** Check container logs in Dockge or use `docker logs nginx-proxy-manager`

</details>
