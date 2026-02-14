FROM python:3.11-slim

# On crée un dossier pour le bot
WORKDIR /app

# On copie les fichiers nécessaires
COPY requirements.txt .
COPY bot.py .
# Si tu as déjà un fichier de sauvegarde, décommente la ligne suivante :
# COPY artisans.json . 

# On installe Discord.py
RUN pip install --no-cache-dir -r requirements.txt

# On lance le bot
CMD ["python", "bot.py"]