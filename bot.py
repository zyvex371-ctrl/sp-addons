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

EXTENSOES_PROIBIDAS = ('.jar', '.exe', '.deb', '.rpm')

def e_arquivo_permitido(url):
    if not url:
        return False
    url_limpa = url.split('?')[0].lower()
    return not any(url_limpa.endswith(ext) for ext in EXTENSOES_PROIBIDAS)

def tratar_url_download(url, categoria):
    """
    Se o link terminar em .zip, ajusta a query para forçar o download 
    reconhecido como .mcaddon ou .mcpack no celular/navegador.
    """
    if not url:
        return url
    
    url_base = url.split('?')[0]
    if url_base.lower().endswith('.zip'):
        ext = ".mcpack" if categoria == "Texturas" else ".mcaddon"
        # Adiciona o parâmetro de nome de arquivo para o navegador tratar como mcaddon/mcpack
        return f"{url}#file{ext}"
    return url

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
    dados = {
        "title": addon["title"],
        "category": addon["category"],
        "version": addon["version"],
        "author": addon["author"],
        "description": addon["description"],
        "image_url": addon["image_url"],
        "download_url": addon["download_url"],
        "downloads": addon.get("downloads", 0)
    }
    if "screenshots" in addon:
        dados["screenshots"] = addon["screenshots"]

    res = requests.post(url, headers=headers_supabase, json=dados)
    if res.status_code in [200, 201]:
        print(f"🔥 Cadastrado no site: {addon['title']} [{addon['category']}] | Downloads: {addon['downloads']}")
    else:
        dados.pop("screenshots", None)
        dados.pop("downloads", None)
        res_retry = requests.post(url, headers=headers_supabase, json=dados)
        if res_retry.status_code in [200, 201]:
            print(f"✅ Cadastrado no site (Modo Simples): {addon['title']}")
        else:
            print(f"❌ Erro ao salvar {addon['title']}: {res.status_code} - {res.text}")

# ==================== CURSEFORGE ====================
def buscar_curseforge(termo, existentes, coletados):
    if not CURSEFORGE_KEY:
        return

    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&classId=4562&searchFilter={termo}&sortField=2&sortOrder=desc&pageSize=30"
    try:
        print(f"🔍 [CurseForge Bedrock] Pesquisando '{termo}'...")
        res = requests.get(url, headers=headers_curseforge)
        if res.status_code == 200:
            mods = res.json().get("data", [])
            for mod in mods:
                titulo = mod.get("name", "").strip()
                downloads = mod.get("downloadCount", 0)

                if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                    continue
                    
                latest_files = mod.get("latestFiles", [])
                download_url = None
                if latest_files:
                    for f in latest_files:
                        f_url = f.get("downloadUrl")
                        if e_arquivo_permitido(f_url):
                            download_url = f_url
                            break
                    
                if not download_url:
                    continue
                    
                desc = mod.get("summary", "Conteúdo incrível para Minecraft Bedrock.")
                authors = ", ".join([a.get("name") for a in mod.get("authors", [])]) or "Comunidade"
                cat = classificar_categoria(titulo, desc)
                
                download_url = tratar_url_download(download_url, cat)
                
                logo = mod.get("logo", {})
                capa = logo.get("thumbnailUrl") or logo.get("url") or "https://via.placeholder.com/400x200"
                screenshots = [s.get("url") for s in mod.get("screenshots", []) if s.get("url")]
                
                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "version": "Bedrock",
                    "author": authors,
                    "description": desc,
                    "image_url": capa,
                    "download_url": download_url,
                    "downloads": downloads,
                    "screenshots": screenshots
                })
    except Exception as e:
        print(f"Erro CurseForge: {e}")

# ==================== MODRINTH ====================
def buscar_modrinth(termo, existentes, coletados):
    print(f"🔍 [Modrinth Bedrock] Pesquisando '{termo}'...")
    url = f'https://api.modrinth.com/v2/search?query={termo}%20bedrock&limit=30&index=downloads'
    try:
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            items = res.json().get("hits", [])
            for item in items:
                titulo = item.get("title", "").strip()
                downloads = item.get("downloads", 0)

                if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                    continue
                    
                project_id = item.get("project_id")
                
                v_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
                v_res = requests.get(v_url, headers={"User-Agent": "SPAddonsBot/1.0"})
                download_url = None
                if v_res.status_code == 200:
                    for ver in v_res.json():
                        for f in ver.get("files", []):
                            file_url = f.get("url")
                            if e_arquivo_permitido(file_url):
                                download_url = file_url
                                break
                        if download_url:
                            break
                            
                if not download_url:
                    continue
                    
                desc = item.get("description", "Conteúdo incrível para Minecraft Bedrock.")
                cat = classificar_categoria(titulo, desc, item.get("categories", []))
                download_url = tratar_url_download(download_url, cat)
                capa = item.get("icon_url") or "https://via.placeholder.com/400x200"

                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "version": "Bedrock",
                    "author": item.get("author", "Comunidade"),
                    "description": desc,
                    "image_url": capa,
                    "download_url": download_url,
                    "downloads": downloads,
                    "screenshots": []
                })
    except Exception as e:
        print(f"Erro Modrinth: {e}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Itens já cadastrados no banco: {len(existentes)}")
    
    coletados = []
    termos = ["action", "weapons", "furniture", "rpg", "animation", "shader", "vehicles"]
    
    for termo in termos:
        buscar_curseforge(termo, existentes, coletados)
        buscar_modrinth(termo, existentes, coletados)

    addons = [item for item in coletados if item['category'] == "Add-ons Bedrock"]
    texturas = [item for item in coletados if item['category'] == "Texturas"]

    addons_para_salvar = sorted(addons, key=lambda x: x['downloads'], reverse=True)[:5]
    texturas_para_salvar = sorted(texturas, key=lambda x: x['downloads'], reverse=True)[:5]

    addons_para_salvar.sort(key=lambda x: x['downloads'])
    texturas_para_salvar.sort(key=lambda x: x['downloads'])

    print(f"\n🚀 Salvando {len(addons_para_salvar)} Addons e {len(texturas_para_salvar)} Texturas no Supabase...")

    for item in addons_para_salvar:
        salvar_no_supabase(item)

    for item in texturas_para_salvar:
        salvar_no_supabase(item)

    print("\n🎉 Finalizado com sucesso!")

if __name__ == "__main__":
    executar_bot()
