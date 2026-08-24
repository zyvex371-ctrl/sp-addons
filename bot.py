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

# Extensões que vamos aceitar. Como estamos buscando SÓ na categoria Bedrock, .zip é seguro.
EXTENSOES_PERMITIDAS = ('.mcaddon', '.mcpack', '.mctemplate', '.zip')

def obter_addons_existentes():
    url = f"{SUPABASE_URL}/rest/v1/addons?select=title"
    try:
        res = requests.get(url, headers=headers_supabase)
        if res.status_code == 200:
            return [item['title'].strip().lower() for item in res.json()]
    except Exception as e:
        print(f"Erro ao buscar banco de dados: {e}")
    return []

def salvar_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    
    # Tratamento de segurança para não quebrar na hora de salvar
    dados = {
        "title": addon["title"],
        "category": addon["category"],
        "version": "Bedrock",
        "author": addon["author"],
        "description": addon["description"],
        "image_url": addon["image_url"],
        "download_url": addon["download_url"]
    }
    
    # Só envia downloads e screenshots se as colunas existirem no seu Supabase
    if "downloads" in addon: dados["downloads"] = addon["downloads"]
    if "screenshots" in addon: dados["screenshots"] = addon["screenshots"]

    res = requests.post(url, headers=headers_supabase, json=dados)
    if res.status_code in [200, 201]:
        print(f"🔥 SALVO COM SUCESSO: {addon['title']}")
    else:
        # Tenta modo de segurança sem colunas extras
        dados.pop("downloads", None)
        dados.pop("screenshots", None)
        res_retry = requests.post(url, headers=headers_supabase, json=dados)
        if res_retry.status_code in [200, 201]:
            print(f"✅ SALVO (Modo Simples): {addon['title']}")
        else:
            print(f"❌ ERRO AO SALVAR {addon['title']}: {res.status_code} - {res.text}")

# ==================== CURSEFORGE (Garantido Bedrock) ====================
def buscar_curseforge(existentes, coletados):
    if not CURSEFORGE_KEY:
        print("⚠️ AVISO: CurseForge Key não encontrada. Adicione no GitHub Secrets.")
        return

    # classId=4562 é a categoria OFICIAL de Addons Bedrock no CurseForge
    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&classId=4562&sortField=2&sortOrder=desc&pageSize=40"
    
    try:
        print(f"🔍 Buscando os melhores Addons no CurseForge...")
        res = requests.get(url, headers=headers_curseforge)
        if res.status_code == 200:
            mods = res.json().get("data", [])
            for mod in mods:
                titulo = mod.get("name", "").strip()
                downloads = mod.get("downloadCount", 0)

                # Se o mod for muito desconhecido, pula. 100 downloads já garante que funciona.
                if downloads < 100:
                    continue

                if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                    continue
                    
                latest_files = mod.get("latestFiles", [])
                download_url = None
                
                if latest_files:
                    for f in latest_files:
                        f_url = f.get("downloadUrl")
                        f_name = f.get("fileName", "").lower()
                        
                        # Verifica se termina com mcaddon, mcpack ou zip
                        if any(f_name.endswith(ext) for ext in EXTENSOES_PERMITIDAS):
                            download_url = f_url
                            break
                    
                if not download_url:
                    continue
                    
                desc = mod.get("summary", "Conteúdo épico para Minecraft Bedrock.")
                authors = ", ".join([a.get("name") for a in mod.get("authors", [])]) or "Comunidade"
                
                # Identifica se é textura
                cat = "Texturas" if any(k in desc.lower() for k in ["texture", "shader", "16x", "pack"]) else "Add-ons Bedrock"
                
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
        print(f"Erro CurseForge: {e}")

# ==================== MODRINTH ====================
def buscar_modrinth(existentes, coletados):
    print(f"🔍 Buscando os melhores Addons no Modrinth...")
    # facet categories:bedrock garante que a pesquisa é só de Bedrock
    url = f'https://api.modrinth.com/v2/search?limit=40&index=downloads&facets=[["categories:bedrock"]]'
    try:
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            items = res.json().get("hits", [])
            for item in items:
                titulo = item.get("title", "").strip()
                downloads = item.get("downloads", 0)

                if downloads < 100:
                    continue

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
                            file_name = f.get("filename", "").lower()
                            
                            if any(file_name.endswith(ext) for ext in EXTENSOES_PERMITIDAS):
                                download_url = file_url
                                break
                        if download_url:
                            break
                            
                if not download_url:
                    continue
                    
                desc = item.get("description", "Conteúdo épico para Minecraft Bedrock.")
                cat = "Texturas" if "resourcepack" in item.get("categories", []) else "Add-ons Bedrock"
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
        print(f"Erro Modrinth: {e}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Seu site já tem {len(existentes)} conteúdos.")
    
    coletados = []
    
    # 1. Faz a busca geral nos dois sites!
    buscar_curseforge(existentes, coletados)
    buscar_modrinth(existentes, coletados)

    if not coletados:
        print("😭 Nenhum mod novo encontrado dessa vez.")
        return

    addons = [item for item in coletados if item['category'] == "Add-ons Bedrock"]
    texturas = [item for item in coletados if item['category'] == "Texturas"]

    # 2. Pega os 8 melhores Addons e as 8 melhores texturas
    addons_para_salvar = sorted(addons, key=lambda x: x['downloads'], reverse=True)[:8]
    texturas_para_salvar = sorted(texturas, key=lambda x: x['downloads'], reverse=True)[:8]

    print(f"\n🚀 ENVIANDO {len(addons_para_salvar)} Addons e {len(texturas_para_salvar)} Texturas para o site...")

    # 3. Salva no banco (do menor para o maior, para o mais popular ficar no TOPO)
    addons_para_salvar.sort(key=lambda x: x['downloads'])
    texturas_para_salvar.sort(key=lambda x: x['downloads'])

    for item in addons_para_salvar:
        salvar_no_supabase(item)

    for item in texturas_para_salvar:
        salvar_no_supabase(item)

    print("\n🎉 CONCLUÍDO! O Bot funcionou e abasteceu o seu site.")

if __name__ == "__main__":
    executar_bot()
