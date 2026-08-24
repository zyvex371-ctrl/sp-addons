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
    if "texture" in texto or "resource" in texto or "textura" in texto or "pack" in texto:
        return "Texturas"
    return "Add-ons Bedrock"

def salvar_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    res = requests.post(url, headers=headers_supabase, json=addon)
    if res.status_code in [200, 201]:
        print(f"✅ Cadastrado no site: {addon['title']} [{addon['category']}]")
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

def buscar_modrinth(index_tipo, existentes, addons_add, texturas_add, limite_addons, limite_texturas):
    termos = ["bedrock", "mcpe", "addon", "texture pack"]
    for termo in termos:
        if addons_add >= limite_addons and texturas_add >= limite_texturas:
            break
            
        print(f"🔍 [Modrinth] Pesquisando '{termo}' (Modo: {index_tipo})...")
        url = f'https://api.modrinth.com/v2/search?query={termo}&limit=50&index={index_tipo}'
        try:
            res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
            if res.status_code == 200:
                items = res.json().get("hits", [])
                for item in items:
                    if addons_add >= limite_addons and texturas_add >= limite_texturas:
                        break
                    
                    titulo = item.get("title", "").strip()
                    if not titulo or titulo.lower() in existentes:
                        continue
                        
                    download_url = obter_arquivo_modrinth(item.get("project_id"))
                    if not download_url:
                        continue
                        
                    desc = item.get("description", "Conteúdo para Minecraft Bedrock.")
                    cat = classificar_categoria(titulo, desc, item.get("categories", []))
                    
                    if cat == "Add-ons Bedrock" and addons_add < limite_addons:
                        salvar_no_supabase({
                            "title": titulo,
                            "category": "Add-ons Bedrock",
                            "version": "Bedrock",
                            "author": item.get("author", "Comunidade"),
                            "description": desc,
                            "image_url": item.get("icon_url") or "https://via.placeholder.com/400x200",
                            "download_url": download_url
                        })
                        existentes.append(titulo.lower())
                        addons_add += 1
                        
                    elif cat == "Texturas" and texturas_add < limite_texturas:
                        salvar_no_supabase({
                            "title": titulo,
                            "category": "Texturas",
                            "version": "Bedrock",
                            "author": item.get("author", "Comunidade"),
                            "description": desc,
                            "image_url": item.get("icon_url") or "https://via.placeholder.com/400x200",
                            "download_url": download_url
                        })
                        existentes.append(titulo.lower())
                        texturas_add += 1
        except Exception as e:
            print(f"Erro na busca Modrinth: {e}")

    return addons_add, texturas_add

# ==================== CURSEFORGE ====================
def buscar_curseforge(sort_field, existentes, addons_add, texturas_add, limite_addons, limite_texturas):
    # sort_field: 2 = Popularidade / Mais Baixados, 3 = Última Atualização / Novos
    if not CURSEFORGE_KEY:
        print("⚠️ Chave CURSEFORGE_KEY não configurada. Pulando CurseForge...")
        return addons_add, texturas_add

    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&sortField={sort_field}&sortOrder=desc&pageSize=50"
    
    try:
        modo_txt = "Novos/Atualizados" if sort_field == 3 else "Mais Populares"
        print(f"🔍 [CurseForge] Buscando conteúdos para Bedrock (Modo: {modo_txt})...")
        res = requests.get(url, headers=headers_curseforge)
        if res.status_code == 200:
            mods = res.json().get("data", [])
            for mod in mods:
                if addons_add >= limite_addons and texturas_add >= limite_texturas:
                    break
                    
                titulo = mod.get("name", "").strip()
                if not titulo or titulo.lower() in existentes:
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
                
                if cat == "Add-ons Bedrock" and addons_add < limite_addons:
                    salvar_no_supabase({
                        "title": titulo,
                        "category": "Add-ons Bedrock",
                        "version": "Bedrock",
                        "author": authors,
                        "description": desc,
                        "image_url": image_url,
                        "download_url": download_url
                    })
                    existentes.append(titulo.lower())
                    addons_add += 1
                    
                elif cat == "Texturas" and texturas_add < limite_texturas:
                    salvar_no_supabase({
                        "title": titulo,
                        "category": "Texturas",
                        "version": "Bedrock",
                        "author": authors,
                        "description": desc,
                        "image_url": image_url,
                        "download_url": download_url
                    })
                    existentes.append(titulo.lower())
                    texturas_add += 1
    except Exception as e:
        print(f"Erro ao buscar no CurseForge: {e}")

    return addons_add, texturas_add

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Itens atualmente cadastrados no banco: {len(existentes)}")
    
    limite_addons = 5
    limite_texturas = 5
    
    addons_add = 0
    texturas_add = 0
    
    # -------------------------------------------------------------
    # FASE 1: Buscar NOVOS nos dois sites
    # -------------------------------------------------------------
    print("=== FASE 1: BUSCANDO NOVOS LANÇAMENTOS ===")
    addons_add, texturas_add = buscar_modrinth("newest", existentes, addons_add, texturas_add, limite_addons, limite_texturas)
    
    if addons_add < limite_addons or texturas_add < limite_texturas:
        addons_add, texturas_add = buscar_curseforge(3, existentes, addons_add, texturas_add, limite_addons, limite_texturas)

    # -------------------------------------------------------------
    # FASE 2: Se ainda faltar, buscar os MAIS POPULARES nos dois sites
    # -------------------------------------------------------------
    if addons_add < limite_addons or texturas_add < limite_texturas:
        print("\n=== FASE 2: COMPLETANDO COM OS MAIS POPULARES ===")
        # Busca os populares na Modrinth
        addons_add, texturas_add = buscar_modrinth("downloads", existentes, addons_add, texturas_add, limite_addons, limite_texturas)
        
        # Se ainda assim faltar, busca os populares no CurseForge
        if addons_add < limite_addons or texturas_add < limite_texturas:
            addons_add, texturas_add = buscar_curseforge(2, existentes, addons_add, texturas_add, limite_addons, limite_texturas)

    print(f"\n🎉 Finalizado! Adicionados {addons_add} Addons e {texturas_add} Texturas nesta rodada.")

if __name__ == "__main__":
    executar_bot()
