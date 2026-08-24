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

def buscar_curseforge(existentes, coletados):
    if not CURSEFORGE_KEY:
        print("⚠️ AVISO: CurseForge Key não encontrada.")
        return

    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&classId=4562&sortField=2&sortOrder=desc&pageSize=50"
    
    try:
        print(f"🔍 Buscando Addons no CurseForge...")
        res = requests.get(url, headers=headers_curseforge)
        if res.status_code == 200:
            mods = res.json().get("data", [])
            print(f"📦 Encontrados {len(mods)} mods brutos na API.")
            
            for mod in mods:
                titulo = mod.get("name", "").strip()
                downloads = mod.get("downloadCount", 0)

                if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                    continue
                    
                latest_files = mod.get("latestFiles", [])
                download_url = None
                
                if latest_files:
                    download_url = latest_files[0].get("downloadUrl")
                    
                if not download_url:
                    links_info = mod.get("links")
                    if isinstance(links_info, dict):
                        download_url = links_info.get("websiteUrl")
                    
                if not download_url:
                    continue
                    
                desc = mod.get("summary", "Conteúdo incrível para Minecraft Bedrock.")
                authors = ", ".join([a.get("name") for a in mod.get("authors", [])]) or "Comunidade"
                
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

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Seu site já tem {len(existentes)} conteúdos.")
    
    coletados = []
    buscar_curseforge(existentes, coletados)

    if not coletados:
        print("😭 Nenhum mod novo para salvar.")
        return

    para_salvar = sorted(coletados, key=lambda x: x['downloads'], reverse=True)[:10]
    para_salvar.sort(key=lambda x: x['downloads'])

    print(f"\n🚀 ENVIANDO {len(para_salvar)} Addons para o Supabase...")
    for item in para_salvar:
        salvar_no_supabase(item)

    print("\n🎉 Processo concluído com sucesso!")

if __name__ == "__main__":
    executar_bot()
