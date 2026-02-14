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
    "Paysan", "Alchimiste", "Bûcheron", "Mineur", 
    "Chasseur", "Pêcheur", "Bricoleur", "Bijoutier", "Cordonnier", 
    "Tailleur", "Forgeron", "Sculpteur", "Joaillomage", "Cordomage", 
    "Costumage", "Forgemage", "Sculptemage", "Façonneur", "Façomage"
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

# --- A. MODALS ---

class SearchModal(ui.Modal, title="Recherche d'artisan"):
    def __init__(self, metier_choisi):
        super().__init__()
        self.metier = metier_choisi
        self.niveau_min = ui.TextInput(
            label=f"Niveau minimum pour {metier_choisi} ?",
            placeholder="Ex: 50",
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.niveau_min)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.niveau_min.value.isdigit():
            await interaction.response.send_message("❌ Le niveau doit être un nombre.", ephemeral=True)
            return

        niveau_min = int(self.niveau_min.value)
        data = load_data()
        found = []

        for user_id, jobs in data.items():
            if self.metier in jobs and jobs[self.metier] >= niveau_min:
                found.append((user_id, jobs[self.metier]))

        # Tri décroissant par niveau
        found.sort(key=lambda x: x[1], reverse=True)

        embed = discord.Embed(
            title=f"🔎 Artisans : {self.metier} (Lvl {niveau_min}+)",
            color=0x00FFFF
        )
        
        description_lines = []
        for uid, level in found:
            member = interaction.guild.get_member(int(uid))
            if member:
                icone = "⭐" if level == 200 else "🔹"
                description_lines.append(f"{icone} **{member.display_name}** | Niveau {level}")
        
        if not description_lines:
            embed.description = f"Aucun artisan trouvée avec ce niveau minimum."
        else:
            embed.description = "\n".join(description_lines)

        await interaction.response.send_message(embed=embed, ephemeral=True)

class UpdateModal(ui.Modal, title="Mise à jour du métier"):
    def __init__(self, metier_choisi):
        super().__init__()
        self.metier = metier_choisi
        self.niveau_input = ui.TextInput(
            label=f"Niveau de {metier_choisi} (0 = Suppr)",
            placeholder="Ex: 200 (ou 0 pour oublier)",
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.niveau_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.niveau_input.value.isdigit():
            await interaction.response.send_message("❌ Le niveau doit être un nombre.", ephemeral=True)
            return
        
        niveau = int(self.niveau_input.value)
        
        if niveau < 0 or niveau > 200:
            await interaction.response.send_message("❌ Le niveau doit être entre 1 et 200 (ou 0 pour supprimer).", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        data = load_data()
        
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=self.metier)

        # Suppression
        if niveau == 0:
            if user_id in data and self.metier in data[user_id]:
                del data[user_id][self.metier]
                # Nettoyage si user vide
                if not data[user_id]:
                    del data[user_id]
                save_data(data)
                
                # Retirer le rôle si présent
                if role and role in interaction.user.roles:
                    try:
                        await interaction.user.remove_roles(role)
                    except discord.Forbidden:
                        pass
                
                await interaction.response.send_message(f"🗑️ Métier **{self.metier}** oublié !", ephemeral=True)
            else:
                await interaction.response.send_message(f"⚠️ Vous n'aviez pas le métier **{self.metier}**.", ephemeral=True)
            return

        # Ajout / Modification
        if user_id not in data:
            data[user_id] = {}
        
        data[user_id][self.metier] = niveau
        save_data(data)

        # Gestion du rôle
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

# --- B. SELECT MENUS ---

class JobSelect(ui.Select):
    def __init__(self, mode="gestion"):
        self.mode = mode
        placeholder_text = "Choisir le métier à rechercher..." if mode == "recherche" else "Choisir le métier à gérer..."
        options = [discord.SelectOption(label=m, value=m) for m in METIERS_DOFUS]
        super().__init__(placeholder=placeholder_text, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.mode == "recherche":
            await interaction.response.send_modal(SearchModal(self.values[0]))
        else:
            await interaction.response.send_modal(UpdateModal(self.values[0]))

class ActionView(ui.View):
    def __init__(self, mode):
        super().__init__()
        self.add_item(JobSelect(mode=mode))

# --- C. MAIN MENU ---

class MainMenu(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # custom_id est nécessaire pour la persistance si le bot redémarre
    
    @ui.button(label="🔎 Rechercher un Artisan", style=discord.ButtonStyle.success, custom_id="btn_search")
    async def search_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Quel métier recherchez-vous ?", view=ActionView(mode="recherche"), ephemeral=True)

    @ui.button(label="🛠️ Gérer mes Métiers", style=discord.ButtonStyle.primary, custom_id="btn_manage")
    async def manage_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Quel métier souhaitez-vous ajouter, modifier ou oublier ?", view=ActionView(mode="gestion"), ephemeral=True)


# --- 4. LE BOT ---
class DofusBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # On ajoute la vue persistante
        self.add_view(MainMenu())
        await self.tree.sync()
        print(f"Commandes synchronisées ! Connecté en tant que {self.user}")

client = DofusBot()

# --- 5. COMMANDES ---

@client.tree.command(name="manager", description="[Admin] Affiche le Manager Dofus (Recherche + Gestion)")
@app_commands.default_permissions(administrator=True)
async def spawn_manager(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🐉 Dofus Manager",
        description="Bienvenue sur le panneau de gestion des métiers.\n\n"
                    "• **Rechercher** : Trouver un artisan disponible.\n"
                    "• **Gérer mes métiers** : Ajouter, mettre à jour ou oublier vos métiers.",
        color=0xFFD700
    )
    embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/fr/3/36/Dofus_Logo.png")
    await interaction.channel.send(embed=embed, view=MainMenu())
    await interaction.response.send_message("Manager créé !", ephemeral=True)

# Lancement
if TOKEN:
    client.run(TOKEN)
else:
    print("ERREUR : Le Token est vide (None). Vérifie tes variables d'environnement.")