import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# --- CONFIGURATION ---
TOKEN = os.getenv('DISCORD_TOKEN')
FICHIER_SAUVEGARDE = 'artisans.json'
if os.path.exists("/app/data"):
    FICHIER_SAUVEGARDE = "/app/data/artisans.json"
# Liste des métiers valides sur Dofus (pour éviter les fautes de frappe)
METIERS_DOFUS = [
    "Paysan", "Boulanger", "Alchimiste", "Bûcheron", "Mineur", 
    "Chasseur", "Pêcheur", "Bricoleur", "Bijoutier", "Cordonnier", 
    "Tailleur", "Forgeron", "Sculpteur", "Joaillomage", "Cordomage", 
    "Costumage", "Forgemage", "Sculptemage", "Façonneur"
]

# --- INITIALISATION ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Important pour gérer les rôles

class DofusBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Synchronise les commandes slash avec Discord au démarrage
        await self.tree.sync()
        print("Commandes synchronisées !")

client = DofusBot()

# Fonction pour charger/sauvegarder les données
def load_data():
    if not os.path.exists(FICHIER_SAUVEGARDE):
        return {}
    with open(FICHIER_SAUVEGARDE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(FICHIER_SAUVEGARDE, 'w') as f:
        json.dump(data, f, indent=4)

# --- COMMANDES ---

@client.tree.command(name="metier", description="Met à jour ton niveau de métier (ex: /metier Paysan 200)")
@app_commands.describe(nom_metier="Choisis le métier", niveau="Ton niveau (1-200)")
@app_commands.choices(nom_metier=[
    app_commands.Choice(name=m, value=m) for m in METIERS_DOFUS
]) 
async def update_metier(interaction: discord.Interaction, nom_metier: str, niveau: int):
    # 1. Vérification du niveau
    if niveau < 1 or niveau > 200:
        await interaction.response.send_message("❌ Le niveau doit être compris entre 1 et 200.", ephemeral=True)
        return

    user_id = str(interaction.user.id)
    guild = interaction.guild

    # 2. Gestion du Rôle Discord (On donne juste le titre, ex: "Boulanger")
    role_name = nom_metier
    role = discord.utils.get(guild.roles, name=role_name)

    # Si le rôle n'existe pas, on le crée
    if not role:
        try:
            role = await guild.create_role(name=role_name, mentionable=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Je n'ai pas la permission de créer des rôles.", ephemeral=True)
            return

    # On donne le rôle à l'utilisateur s'il ne l'a pas
    if role not in interaction.user.roles:
        try:
            await interaction.user.add_roles(role)
        except discord.Forbidden:
             await interaction.response.send_message("❌ Je ne peux pas t'attribuer ce rôle (vérifie ma hiérarchie).", ephemeral=True)
             return

    # 3. Sauvegarde des données dans le fichier JSON
    data = load_data()
    
    if user_id not in data:
        data[user_id] = {}
    
    # On enregistre le niveau
    data[user_id][nom_metier] = niveau
    save_data(data)

    await interaction.response.send_message(f"✅ **{nom_metier}** mis à jour au niveau **{niveau}** ! Tu as reçu le rôle correspondant.", ephemeral=True)


@client.tree.command(name="profil", description="Affiche les métiers d'un joueur")
async def show_profil(interaction: discord.Interaction, membre: discord.Member = None):
    # Si aucun membre n'est précisé, on prend l'auteur de la commande
    target = membre or interaction.user
    user_id = str(target.id)
    
    data = load_data()

    if user_id not in data or not data[user_id]:
        await interaction.response.send_message(f"😕 {target.display_name} n'a pas encore enregistré de métiers.", ephemeral=True)
        return

    # Création d'un joli Embed (Carte de visite)
    embed = discord.Embed(title=f"🛠️ Livre des artisans : {target.display_name}", color=0x00ff00)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)

    description = ""
    # On trie les métiers par niveau décroissant (les 200 en premier)
    sorted_jobs = sorted(data[user_id].items(), key=lambda x: x[1], reverse=True)

    for metier, niveau in sorted_jobs:
        icone = "⭐" if niveau == 200 else "🔹"
        description += f"{icone} **{metier}** : Niv. {niveau}\n"

    embed.description = description
    await interaction.response.send_message(embed=embed)


@client.tree.command(name="team", description="Affiche les métiers de toute l'équipe")
async def show_team(interaction: discord.Interaction):
    data = load_data()

    if not data:
        await interaction.response.send_message("❌ Personne n'a encore enregistré de métier.", ephemeral=True)
        return

    # On prépare un joli tableau
    embed = discord.Embed(title="🛡️ L'équipe des Artisans", description="Voici les compétences du groupe :", color=0xFFA500)
    
    # Compteur pour savoir si on a trouvé des gens
    count = 0

    # On parcourt chaque joueur enregistré dans le fichier JSON
    for user_id, jobs in data.items():
        # On essaie de retrouver le membre sur le serveur
        member = interaction.guild.get_member(int(user_id))

        # Si le membre est bien sur le serveur (et pas parti)
        if member:
            count += 1
            description = ""
            
            # On trie ses métiers (les 200 en haut)
            sorted_jobs = sorted(jobs.items(), key=lambda x: x[1], reverse=True)

            # On formate le texte (Max 5 métiers par personne pour pas faire trop long, modifiable)
            for metier, niveau in sorted_jobs:
                icone = "⭐" if niveau == 200 else "🔹"
                description += f"{icone} **{metier}** : {niveau}\n"

            if description == "":
                description = "Pas de métier enregistré"

            # On ajoute une case dans le tableau pour ce joueur
            # inline=True permet de les mettre côte à côte
            embed.add_field(name=f"👤 {member.display_name}", value=description, inline=True)

    if count == 0:
        await interaction.response.send_message("❌ Aucun artisan trouvé sur le serveur.", ephemeral=True)
    else:
        # Note : J'ai mis ephemeral=False ici pour que tout le monde puisse voir l'équipe
        # Si tu veux que ce soit privé, change False en True
        await interaction.response.send_message(embed=embed, ephemeral=False)

client.run(TOKEN)