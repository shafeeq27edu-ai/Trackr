# Backup & Recovery Guide — Trackr v1.0

A reliable backup and recovery system ensures business continuity and protects against database corruption, hardware failures, and user errors.

---

## 1. Scope of Backup

A complete Trackr backup consists of three distinct components:
1. **Application Database**: The SQLite file containing workspaces, user details, job statuses, audit trails, and stream setups.
2. **Uploaded & Processed Assets**: Bounding-box video outputs, heatmaps, and uploaded source files.
3. **Environment and Configurations**: Config files, secrets (`.env`), and custom analytics zone definitions.

| Asset Type | Primary Location | Backup Frequency | Target Format |
| :--- | :--- | :--- | :--- |
| Database | `object-tracker/trackr.db` | Daily (Incremental / Full) | `.sql` or copied `.db` |
| Uploaded Media | `object-tracker/data/temp/` | Weekly | Compressed Archive `.tar.gz` |
| Processed Outputs | `object-tracker/outputs/api/` | Daily | Compressed Archive `.tar.gz` |
| Environment Config | `object-tracker/.env` & `config/` | On Change | Secure Text Store |

---

## 2. Backup Strategy

### 2.1 Database Backups (SQLite Safe Copy)
Directly copying a running SQLite database file while writes are active can lead to corruption. Use the SQLite `.backup` API or copy the file safely:

```bash
# Perform a safe online backup of the SQLite database
sqlite3 object-tracker/trackr.db ".backup 'backups/db/trackr_backup_$(date +%F).db'"
```

### 2.2 Assets and Media Backups
Compress input/output assets using `tar`:
```bash
# Archive all processed video analytics and heatmaps
tar -czf backups/assets/outputs_$(date +%F).tar.gz object-tracker/outputs/
```

---

## 3. Automated Backup Script

The following script (`scripts/backup.sh`) handles automatic daily backups. Ensure it has execute permissions (`chmod +x scripts/backup.sh`):

```bash
#!/bin/bash
# scripts/backup.sh - Trackr Automated Backup

BACKUP_DIR="backups/$(date +%F)"
mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/assets"

echo "Starting Trackr backup..."

# 1. Database backup
sqlite3 object-tracker/trackr.db ".backup '$BACKUP_DIR/db/trackr.db'"

# 2. Archive config and secrets
cp object-tracker/.env "$BACKUP_DIR/"
cp -r object-tracker/config "$BACKUP_DIR/config"

# 3. Archive output assets
tar -czf "$BACKUP_DIR/assets/outputs.tar.gz" -C object-tracker outputs/

echo "Backup completed successfully at $BACKUP_DIR"
```

To schedule daily at 02:00 AM, add a cron job:
```cron
0 2 * * * /bin/bash /app/scripts/backup.sh > /var/log/trackr-backup.log 2>&1
```

---

## 4. Restore & Recovery Procedures

### 4.1 Database Restore
To restore the database to a specific snapshot:
1. Stop the application backend services:
   ```bash
   docker compose down
   ```
2. Rename the current database file to prevent accidental loss:
   ```bash
   mv object-tracker/trackr.db object-tracker/trackr.db.bak
   ```
3. Copy the backup file into the active workspace:
   ```bash
   cp backups/2026-07-10/db/trackr.db object-tracker/trackr.db
   ```
4. Restart the services:
   ```bash
   docker compose up -d
   ```

### 4.2 Asset Restore
To restore uploaded files or processed tracking outputs:
```bash
# Restore output videos and analytics
tar -xzf backups/2026-07-10/assets/outputs.tar.gz -C object-tracker/
```

---

## 5. Recovery Testing Protocol

Verify backups monthly:
1. Deploy a separate "Restore Test" environment (e.g. Docker container on port `8080`).
2. Restore the database and asset files into this container using the procedures above.
3. Call `/api/v1/system/health` to verify service initialization.
4. Log in and load historical jobs to verify integrity.
