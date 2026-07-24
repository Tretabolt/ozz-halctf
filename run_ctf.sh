#!/bin/bash
# CTF full run script — keeps Docker alive, polls for MySQL readiness
set -e

echo "[1/5] Starting Docker daemon..."
sudo -n service docker start 2>/dev/null || sudo service docker start 2>/dev/null || true
sleep 3

echo "[2/5] Starting all containers..."
cd '/mnt/c/Users/Daniel Palma/Documents/antigravity/clever-pythagoras/ozz-halctf/universe'
sudo docker compose up -d 2>&1

echo "[3/5] Waiting for MySQL to be ready (up to 120s)..."
for i in $(seq 1 60); do
    if sudo docker exec target-04 mysqladmin -u root -pMySQL_R00t_2026! ping --silent 2>/dev/null; then
        echo "  MySQL ready after ${i}s"
        break
    fi
    echo "  ...waiting ($i/60)"
    sleep 2
done

echo "[4/5] Granting MySQL TCP access from any host..."
sudo docker exec target-04 mysql -u root -pMySQL_R00t_2026! -e \
  "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'MySQL_R00t_2026!' WITH GRANT OPTION; FLUSH PRIVILEGES;" 2>&1 || true

echo "[4b/5] Verifying MySQL flags table..."
sudo docker exec target-04 mysql -u root -pMySQL_R00t_2026! corporate \
  -e "SELECT secret_key, secret_value FROM internal_secrets;" 2>&1

echo "[5/5] All containers status:"
sudo docker ps

echo ""
echo "Running attack.py..."
cd '/mnt/c/Users/Daniel Palma/Documents/antigravity/clever-pythagoras/ozz-halctf'
PYTHONUTF8=1 python3 attack.py --verbose 2>&1
