import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
CURSEFORGE_KEY = os.environ.get("CURSEFORGE_KEY")

headers_supabase = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

headers_curseforge = {
    "x-api-key": CURSEFORGE_KEY,
    "Accept": "application/json"
}

def obter_addons_existentes():
    url = f"{SUPABASE_URL}/rest/v1/addons?select=title"
    try:
        res = requests.get(url, headers=headers_supabase)
        if res.status_code == 200:
            return [item['title'].strip().lower() for item in res.json()]
    except Exception as e:
        print(f"Erro ao buscar existentes: {e}")
    return []

def classificar_categoria(titulo, descricao, tags=""):
    texto = (str(titulo) + " " + str(descricao) + " " + str(tags)).lower()
    if any(k in texto for k in ["texture", "resource", "textura", "shader", "pack", "16x", "32x", "64x"]):
        return "Texturas"
    return "Add-ons Bedrock"

def salvar_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    res = requests.post(url, headers=headers_supabase, json=addon)
    if res.status_code in [200, 201]:
        print(f"🔥 Cadastrado no site: {addon['title']} [{addon['category']}] | Downloads: {addon['downloads']}")
    else:
        print(f"❌ Erro ao salvar {addon['title']}: {res.status_code} - {res.text}")

# ==================== MODRINTH ====================
def obter_arquivo_modrinth(project_id):
    try:
        url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            versions = res.json()
            for ver in versions:
                files = ver.get("files", [])
                if files:
                    return files[0].get("url")
    except Exception as e:
        print(f"Erro Modrinth versão {project_id}: {e}")
    return None

def buscar_modrinth(termo, existentes, coletados):
    print(f"🔍 [Modrinth] Pesquisando '{termo}'...")
    url = f'https://api.modrinth.com/v2/search?query={termo}&limit=50&index=downloads'
    try:
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            items = res.json().get("hits", [])
            for item in items:
                titulo = item.get("title", "").strip()
                if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                    continue
                    
                download_url = obter_arquivo_modrinth(item.get("project_id"))
                if not download_url:
                    continue
                    
                desc = item.get("description", "Conteúdo épico para Minecraft Bedrock.")
                cat = classificar_categoria(titulo, desc, item.get("categories", []))
                
                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "version": "Bedrock",
                    "author": item.get("author", "Comunidade"),
                    "description": desc,
                    "image_url": item.get("icon_url") or "https://via.placeholder.com/400x200",
                    "download_url": download_url,
                    "downloads": item.get("downloads", 0)
                })
    except Exception as e:
        print(f"Erro na busca Modrinth: {e}")

# ==================== CURSEFORGE ====================
def buscar_curseforge(termo, existentes, coletados):
    if not CURSEFORGE_KEY:
        return

    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter={termo}&sortField=2&sortOrder=desc&pageSize=50"
    try:
        print(f"🔍 [CurseForge] Pesquisando '{termo}'...")
        res = requests.get(url, headers=headers_curseforge)
        if res.status_code == 200:
            mods = res.json().get("data", [])
            for mod in mods:
                titulo = mod.get("name", "").strip()
                if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                    continue
                    
                latest_files = mod.get("latestFiles", [])
                download_url = None
                if latest_files:
                    download_url = latest_files[0].get("downloadUrl")
                    
                if not download_url:
                    continue
                    
                desc = mod.get("summary", "Conteúdo extraído do CurseForge.")
                authors = ", ".join([a.get("name") for a in mod.get("authors", [])]) or "Comunidade"
                logo = mod.get("logo", {})
                image_url = logo.get("thumbnailUrl") or logo.get("url") or "https://via.placeholder.com/400x200"
                cat = classificar_categoria(titulo, desc)
                
                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "version": "Bedrock",
                    "author": authors,
                    "description": desc,
                    "image_url": image_url,
                    "download_url": download_url,
                    "downloads": mod.get("downloadCount", 0)
                })
    except Exception as e:
        print(f"Erro ao buscar no CurseForge: {e}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Itens já cadastrados no banco: {len(existentes)}")
    
    coletados = []
    termos_massa = ["action", "rpg", "animation", "weapons", "furniture", "realistic", "shader", "pvp", "vehicles"]
    
    # 1. Coleta conteúdos populares de cada termo
    for termo in termos_massa:
        buscar_modrinth(termo, existentes, coletados)
        buscar_curseforge(termo, existentes, coletados)

    # 2. Separa em Addons e Texturas
    addons = [item for item in coletados if item['category'] == "Add-ons Bedrock"]
    texturas = [item for item in coletados if item['category'] == "Texturas"]

    # 3. Ordena do MENOR para o MAIOR número de downloads
    # Assim, o que tiver MAIS downloads é salvo por ÚLTIMO e fica no TOPO do site!
    addons_para_salvar = sorted(addons, key=lambda x: x['downloads'])[:5]
    texturas_para_salvar = sorted(texturas, key=lambda x: x['downloads'])[:5]

    # Reordena novamente os 5 selecionados para garantir que o com maior número seja enviado por último
    addons_para_salvar.sort(key=lambda x: x['downloads'])
    texturas_para_salvar.sort(key=lambda x: x['downloads'])

    print(f"\n🚀 Salvando os {len(addons_para_salvar)} Addons e {len(texturas_para_salvar)} Texturas mais populares no Supabase...")

    # 4. Envia para o Supabase
    for item in addons_para_salvar:
        salvar_no_supabase(item)

    for item in texturas_para_salvar:
        salvar_no_supabase(item)

    print("\n🎉 Finalizado! Os mods mais famosos foram adicionados por último e ficaram no topo do seu site.")

if __name__ == "__main__":
    executar_bot()
