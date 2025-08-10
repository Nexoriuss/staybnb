\
#!/usr/bin/env bash
# Staybnb - demarrage facile (macOS / Linux)
set -e
echo "=== Staybnb (macOS/Linux) ==="
if ! command -v python3 >/dev/null 2>&1; then
  echo "Erreur : Python3 n'est pas installe. Installe-le via https://www.python.org/downloads/ ou 'brew install python'."
  exit 1
fi
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python3 app.py
