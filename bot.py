import discord
from discord import app_commands, ui
from discord.ext import commands
import json
import os

# --- 1. CONFIGURATION ---
# Récupération du token
TOKEN = os.getenv('DISCORD_TOKEN')

# Gestion du fichier de sauvegarde (Persistance)
if os.path.exists("/app/data"):
    FICHIER_SAUVEGARDE = "/app/data/artisans.json"
else:
    FICHIER_SAUVEGARDE = "artisans.json"

METIERS_DOFUS = [
    "Paysan", "Boulanger", "Alchimiste", "Bûcheron", "Mineur", 
    "Chasseur", "Pêcheur", "Bricoleur", "Bijoutier", "Cordonnier", 
    "Tailleur", "Forgeron", "Sculpteur", "Joaillomage", "Cordomage", 
    "Costumage", "Forgemage", "Sculptemage", "Façonneur"
]

# --- 2. FONCTIONS UTILES ---
def load_data():
    if not os.path.exists(FICHIER_SAUVEGARDE):
        return {}
    try:
        with open(FICHIER_SAUVEGARDE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(FICHIER_SAUVEGARDE, 'w') as f:
        json.dump(data, f, indent=4)

# --- 3. INTERFACE GRAPHIQUE (UI) ---

class LevelModal(ui.Modal, title="Mise à jour du niveau"):
    def __init__(self, metier_choisi):
        super().__init__()
        self.metier = metier_choisi
        self.niveau_input = ui.TextInput(
            label=f"Niveau de {metier_choisi} ?",
            placeholder="Ex: 200",
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.niveau_input)

    async def on_submit(self, interaction: discord.Interaction):
        niveau_str = self.niveau_input.value
        
        if not niveau_str.isdigit():
            await interaction.response.send_message("❌ Le niveau doit être un nombre.", ephemeral=True)
            return
        
        niveau = int(niveau_str)
        if niveau < 1 or niveau > 200:
            await interaction.response.send_message("❌ Le niveau doit être entre 1 et 200.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        data = load_data()
        if user_id not in data:
            data[user_id] = {}
        
        data[user_id][self.metier] = niveau
        save_data(data)

        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=self.metier)
        
        if not role:
            try:
                role = await guild.create_role(name=self.metier, mentionable=True)
            except discord.Forbidden:
                pass 

        if role and role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(role)
            except discord.Forbidden:
                pass

        await interaction.response.send_message(f"✅ **{self.metier}** mis à jour au niveau **{niveau}** !", ephemeral=True)

class JobSelect(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=m, value=m) for m in METIERS_DOFUS]
        super().__init__(placeholder="Choisis un métier dans la liste...", min_values=1, max_values=1, options=options, custom_id="job_select")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LevelModal(self.values[0]))

class JobView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(JobSelect())

# --- 4. LE BOT ---
class DofusBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(JobView())
        await self.tree.sync()
        print(f"Commandes synchronisées ! Connecté en tant que {self.user}")

client = DofusBot()

# --- 5. COMMANDES ---

@client.tree.command(name="panel", description="[Admin] Affiche le panneau des métiers")
@app_commands.default_permissions(administrator=True)
async def spawn_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ Gestion de vos Métiers",
        description="Sélectionnez votre métier ci-dessous pour mettre à jour votre niveau.",
        color=0x00ff00
    )
    await interaction.channel.send(embed=embed, view=JobView())
    await interaction.response.send_message("Panneau créé !", ephemeral=True)

@client.tree.command(name="team", description="Affiche les métiers de toute l'équipe")
async def show_team(interaction: discord.Interaction):
    data = load_data()
    if not data:
        await interaction.response.send_message("❌ Personne n'a encore enregistré de métier.", ephemeral=True)
        return

    embed = discord.Embed(title="🛡️ L'équipe des Artisans", description="Compétences du groupe :", color=0xFFA500)
    count = 0
    for user_id, jobs in data.items():
        member = interaction.guild.get_member(int(user_id))
        if member:
            count += 1
            description = ""
            sorted_jobs = sorted(jobs.items(), key=lambda x: x[1], reverse=True)
            for metier, niveau in sorted_jobs:
                icone = "⭐" if niveau == 200 else "🔹"
                description += f"{icone} **{metier}** : {niveau}\n"
            embed.add_field(name=f"👤 {member.display_name}", value=description or "Aucun", inline=True)

    if count == 0:
        await interaction.response.send_message("❌ Aucun artisan trouvé sur le serveur.", ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed)

@client.tree.command(name="profil", description="Affiche les métiers d'un joueur")
async def show_profil(interaction: discord.Interaction, membre: discord.Member = None):
    target = membre or interaction.user
    user_id = str(target.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message(f"😕 {target.display_name} n'a pas enregistré de métiers.", ephemeral=True)
        return
    embed = discord.Embed(title=f"Artisan : {target.display_name}", color=0x00ff00)
    desc = ""
    for m, n in sorted(data[user_id].items(), key=lambda x: x[1], reverse=True):
        desc += f"**{m}** : {n}\n"
    embed.description = desc
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Lancement
if TOKEN:
    client.run(TOKEN)
else:
    print("ERREUR : Le Token est vide (None). Vérifie tes variables d'environnement.")