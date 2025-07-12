# Netbox_db_Manager v1 (netbox on Synology NAS or local server)

A lightweight and efficient terminal-based Python application to manage PostgreSQL exports and imports for multiple Dockerized NetBox instances hosted on a Synology NAS or local Linux servers.

## Overview

This project simplifies the process of backing up, restoring, and migrating NetBox PostgreSQL databases. It supports secure SSH-based transfers and ensures data integrity through hash verification.

The entire workflow is designed to be executed from the command line on a Windows machine using Git Bash, enabling fast and controlled operations.

## Key Features

- Simple and efficient **terminal-based CLI interface**
- **CSV-based instance management** with centralized configuration
- **Export SQL** databases from NAS or local servers
- **Import SQL** backups with SHA256 integrity verification
- **Secure SSH connections** to both NAS and local NetBox servers
- Requires **RSA key authentication** for the NAS
- **Step-by-step validation** at every stage of the process

## Prerequisites

### Environment

- **Host system**: Windows with **Git Bash** installed (required for UNIX-compatible commands)
- **Remote systems**:
  - Synology NAS with Docker and SSH enabled
  - Optional: local Linux-based NetBox server (e.g., Ubuntu) with Docker

### Access & Security

- SSH access to both the NAS and the local server
- **RSA private key** configured for password-less SSH login to the NAS
- **`sudo` password** will be prompted and stored temporarily for remote operations if needed

### Directory Structure

```
network_db_manager/
├── backend/
│   ├── auth_session.py          # Manages SSH/sudo credentials
│   ├── csv_utils.py             # Loads source list from CSV
│   ├── export_utils.py          # Export logic (SSH, Docker, hash)
│   ├── import_utils.py          # Import logic (verify, SCP, inject)
│   ├── hash_utils.py            # SHA256 calculations
├── frontend/
│   └── main_cli.py              # User-facing CLI logic
├── frontend.py                  # CLI UI & dispatcher
├── main.py                      # Entry point
├── sources.csv                  # List of NetBox instances
├── exported_database/
│   └── exported_netbox_database.sql
└── README.md
```



## sources.csv Format

The `sources.csv` file defines all known NetBox environments:

```csv
name,ip,container
netbox-stock,192.168.1.20,netbox-stock
netbox-local,192.168.1.10,netbox-local
name: Logical identifier of the instance

ip: IP address of the host (NAS or local)

container: Docker container name that holds the PostgreSQL database

The system detects whether a source is local or remote based on the name and ip.

Author
Julien Gaulier
GRAVITY MEDIA
gaulierjulien@yahoo.fr

License
This project is licensed under the MIT License.
