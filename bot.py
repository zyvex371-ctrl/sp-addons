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

def e_arquivo_valido(url_ou_nome):
    if not url_ou_nome:
        return False
    texto = url_ou_nome.lower()
    # Barre arquivos de Java de vez
    if '.jar' in texto or '.mrpack' in texto or '.exe' in texto or '.rar' in texto:
        return False
    return True

def ajustar_link_para_bedrock(url, categoria):
    """
    Garante que o link termine com a extensão correta do Bedrock 
    para que o celular abra direto no Minecraft ao baixar.
    """
    if not url:
        return url
    
    # Se for link do CurseForge ou Modrinth que termina em zip, 
    # adicionamos um truque de parâmetros para o navegador forçar o download correto
    if categoria == "Texturas":
        return f"{url}#file.mcpack"
    else:
        return f"{url}#file.mcaddon"

def obter_addons_existentes():
    url = f"{SUPABASE_URL}/rest/v1/addons?select=title"
    try:
        res = requests.get(url, headers=headers_supabase)
        if res.status_code == 200:
            return [item['title'].strip().lower() for item in res.json()]
    except Exception as e:
        print(f"Erro ao buscar banco: {e}")
    return []

def salvar_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    dados = {
        "title": addon["title"],
        "category": addon["category"],
        "version": "Bedrock",
        "author": addon["author"],
        "description": addon["description"],
        "image_url": addon["image_url"],
        "download_url": addon["download_url"]
    }
    
    if "downloads" in addon: dados["downloads"] = addon["downloads"]
    if "screenshots" in addon: dados["screenshots"] = addon["screenshots"]

    res = requests.post(url, headers=headers_supabase, json=dados)
    if res.status_code in [200, 201]:
        print(f"🔥 SALVO NO SITE: {addon['title']}")
    else:
        dados.pop("downloads", None)
        dados.pop("screenshots", None)
        res_retry = requests.post(url, headers=headers_supabase, json=dados)
        if res_retry.status_code in [200, 201]:
            print(f"✅ SALVO (Modo Simples): {addon['title']}")
        else:
            print(f"❌ ERRO AO SALVAR {addon['title']}: {res.status_code} - {res.text}")

# ==================== CURSEFORGE ====================
def buscar_curseforge(termo, existentes, coletados):
    if not CURSEFORGE_KEY:
        return

    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter={termo}%20bedrock&sortField=2&sortOrder=desc&pageSize=15"
    try:
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
                file_name = ""
                
                if latest_files:
                    download_url = latest_files[0].get("downloadUrl")
                    file_name = latest_files[0].get("fileName", "")
                    
                if not e_arquivo_valido(file_name) or not e_arquivo_valido(download_url):
                    continue
                    
                if not download_url:
                    links_info = mod.get("links")
                    if isinstance(links_info, dict):
                        download_url = links_info.get("websiteUrl")
                    
                if not download_url:
                    continue
                    
                desc = mod.get("summary", "Conteúdo incrível para Minecraft Bedrock.")
                authors = ", ".join([a.get("name") for a in mod.get("authors", [])]) or "Comunidade"
                cat = "Texturas" if any(k in desc.lower() for k in ["texture", "shader", "16x", "pack"]) else "Add-ons Bedrock"
                
                # Ajusta o link de download para forçar a extensão correta
                download_url = ajustar_link_para_bedrock(download_url, cat)
                
                logo = mod.get("logo", {})
                capa = logo.get("thumbnailUrl") or logo.get("url") or "https://via.placeholder.com/400x200"
                screenshots = [s.get("url") for s in mod.get("screenshots", []) if s.get("url")][:4]
                
                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "author": authors,
                    "description": desc,
                    "image_url": capa,
                    "download_url": download_url,
                    "downloads": downloads,
                    "screenshots": screenshots
                })
    except Exception as e:
        print(f"Erro CurseForge {termo}: {e}")

# ==================== MODRINTH ====================
def buscar_modrinth(termo, existentes, coletados):
    url = f'https://api.modrinth.com/v2/search?query={termo}%20bedrock&limit=15&index=downloads'
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
                file_name = ""
                
                if v_res.status_code == 200:
                    versions = v_res.json()
                    if versions:
                        files = versions[0].get("files", [])
                        if files:
                            download_url = files[0].get("url")
                            file_name = files[0].get("filename", "")
                            
                if not e_arquivo_valido(file_name) or not e_arquivo_valido(download_url):
                    continue
                            
                if not download_url:
                    download_url = f"https://modrinth.com/mod/{project_id}"
                    
                desc = item.get("description", "Conteúdo incrível para Minecraft Bedrock.")
                cat = "Texturas" if "resourcepack" in item.get("categories", []) else "Add-ons Bedrock"
                
                # Ajusta o link de download para forçar a extensão correta
                download_url = ajustar_link_para_bedrock(download_url, cat)
                
                capa = item.get("icon_url") or "https://via.placeholder.com/400x200"

                coletados.append({
                    "title": titulo,
                    "category": cat,
                    "author": item.get("author", "Comunidade"),
                    "description": desc,
                    "image_url": capa,
                    "download_url": download_url,
                    "downloads": downloads,
                    "screenshots": []
                })
    except Exception as e:
        print(f"Erro Modrinth {termo}: {e}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Seu site já tem {len(existentes)} conteúdos.")
    
    coletados = []
    termos = ["addon", "furniture", "weapons", "rpg", "shader", "vehicles"]
    
    for termo in termos:
        print(f"🔍 Pesquisando por '{termo} bedrock'...")
        buscar_curseforge(termo, existentes, coletados)
        buscar_modrinth(termo, existentes, coletados)

    if not coletados:
        print("😭 Nenhum mod Bedrock puro encontrado.")
        return

    para_salvar = sorted(coletados, key=lambda x: x['downloads'], reverse=True)[:8]
    para_salvar.sort(key=lambda x: x['downloads'])

    print(f"\n🚀 ENVIANDO {len(para_salvar)} Addons corrigidos para o Supabase...")
    for item in para_salvar:
        salvar_no_supabase(item)

    print("\n🎉 Processo concluído com links otimizados!")

if __name__ == "__main__":
    executar_bot()
