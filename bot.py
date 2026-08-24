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
} if CURSEFORGE_KEY else {}

EXTENSOES_INVALIDAS = ('.jar', '.exe', '.deb', '.rpm')

def e_arquivo_valido(url):
    if not url:
        return False
    url_limpa = url.split('?')[0].lower()
    if any(url_limpa.endswith(ext) for ext in EXTENSOES_INVALIDAS):
        return False
    return True

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
    
    # Prepara objeto seguro (se screenshots ou downloads faltarem, ele não quebra)
    dados = {
        "title": addon["title"],
        "category": addon["category"],
        "version": addon["version"],
        "author": addon["author"],
        "description": addon["description"],
        "image_url": addon["image_url"],
        "download_url": addon["download_url"]
    }
    
    if "downloads" in addon:
        dados["downloads"] = addon["downloads"]
    if "screenshots" in addon:
        dados["screenshots"] = addon["screenshots"]

    res = requests.post(url, headers=headers_supabase, json=dados)
    if res.status_code in [200, 201]:
        print(f"🔥 Cadastrado no site: {addon['title']} [{addon['category']}]")
    else:
        # Se der erro de coluna faltando, tenta sem downloads/screenshots
        dados.pop("downloads", None)
        dados.pop("screenshots", None)
        res_retry = requests.post(url, headers=headers_supabase, json=dados)
        if res_retry.status_code in [200, 201]:
            print(f"✅ Cadastrado no site (Modo Simples): {addon['title']}")
        else:
            print(f"❌ Erro ao salvar {addon['title']}: {res.status_code} - {res.text}")

# ==================== MODRINTH ====================
def obter_dados_extras_modrinth(project_id):
    download_url = None
    screenshots = []
    try:
        v_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        v_res = requests.get(v_url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if v_res.status_code == 200:
            versions = v_res.json()
            for ver in versions:
                files = ver.get("files", [])
                for f in files:
                    file_url = f.get("url")
                    if e_arquivo_valido(file_url):
                        download_url = file_url
                        break
                if download_url:
                    break

        p_url = f"https://api.modrinth.com/v2/project/{project_id}"
        p_res = requests.get(p_url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if p_res.status_code == 200:
            gallery = p_res.json().get("gallery", [])
            screenshots = [img.get("url") for img in gallery if img.get("url")]
    except Exception as e:
        print(f"Erro Modrinth {project_id}: {e}")
        
    return download_url, screenshots

def buscar_modrinth(termo, existentes, coletados):
    print(f"🔍 [Modrinth] Pesquisando '{termo}'...")
    url = f'https://api.modrinth.com/v2/search?query={termo}%20bedrock&limit=30&index=downloads'
    try:
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            items = res.json().get("hits", [])
            for item in items:
                titulo = item.get("title", "").strip()
                if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                    continue
                    
                download_url, screenshots = obter_dados_extras_modrinth(item.get("project_id"))
                if not download_url:
                    continue
                    
                desc = item.get("description", "Conteúdo incrível para Minecraft Bedrock.")
                cat = classificar_categoria(titulo, desc, item.get("categories", []))
                capa = item.get("icon_url") or (screenshots[0] if screenshots else "https://via.placeholder.com/400x200")

                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "version": "Bedrock",
                    "author": item.get("author", "Comunidade"),
                    "description": desc,
                    "image_url": capa,
                    "download_url": download_url,
                    "downloads": item.get("downloads", 0),
                    "screenshots": screenshots
                })
    except Exception as e:
        print(f"Erro na busca Modrinth: {e}")

# ==================== CURSEFORGE ====================
def buscar_curseforge(termo, existentes, coletados):
    if not CURSEFORGE_KEY:
        print("⚠️ CurseForge Key não detectada nas variáveis de ambiente.")
        return

    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter={termo}&sortField=2&sortOrder=desc&pageSize=30"
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
                    for f in latest_files:
                        f_url = f.get("downloadUrl")
                        if e_arquivo_valido(f_url):
                            download_url = f_url
                            break
                    
                if not download_url:
                    continue
                    
                desc = mod.get("summary", "Conteúdo extraído do CurseForge.")
                authors = ", ".join([a.get("name") for a in mod.get("authors", [])]) or "Comunidade"
                
                logo = mod.get("logo", {})
                capa = logo.get("thumbnailUrl") or logo.get("url") or "https://via.placeholder.com/400x200"
                screenshots = [s.get("url") for s in mod.get("screenshots", []) if s.get("url")]
                cat = classificar_categoria(titulo, desc)
                
                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "version": "Bedrock",
                    "author": authors,
                    "description": desc,
                    "image_url": capa,
                    "download_url": download_url,
                    "downloads": mod.get("downloadCount", 0),
                    "screenshots": screenshots
                })
    except Exception as e:
        print(f"Erro CurseForge: {e}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Itens já cadastrados no banco: {len(existentes)}")
    
    coletados = []
    termos = ["bedrock", "addon", "mcpe", "texture", "rpg", "furniture", "shader"]
    
    for termo in termos:
        buscar_modrinth(termo, existentes, coletados)
        buscar_curseforge(termo, existentes, coletados)

    addons = [item for item in coletados if item['category'] == "Add-ons Bedrock"]
    texturas = [item for item in coletados if item['category'] == "Texturas"]

    # Seleciona os de maior download
    addons_para_salvar = sorted(addons, key=lambda x: x['downloads'])[:5]
    texturas_para_salvar = sorted(texturas, key=lambda x: x['downloads'])[:5]

    # Ordena para salvar os maiores por último (ficando no topo do site)
    addons_para_salvar.sort(key=lambda x: x['downloads'])
    texturas_para_salvar.sort(key=lambda x: x['downloads'])

    print(f"\n🚀 Salvando {len(addons_para_salvar)} Addons e {len(texturas_para_salvar)} Texturas no Supabase...")

    for item in addons_para_salvar:
        salvar_no_supabase(item)

    for item in texturas_para_salvar:
        salvar_no_supabase(item)

    print("\n🎉 Finalizado!")

if __name__ == "__main__":
    executar_bot()
