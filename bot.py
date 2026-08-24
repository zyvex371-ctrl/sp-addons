import os
import io
import zipfile
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

def enviar_arquivo_para_storage(arquivo_bytes, nome_arquivo):
    storage_url = f"{SUPABASE_URL}/storage/v1/object/addons-media/{nome_arquivo}"
    headers_storage = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/octet-stream",
        "x-upsert": "true"
    }
    
    res = requests.post(storage_url, headers=headers_storage, data=arquivo_bytes)
    if res.status_code in [200, 201]:
        return f"{SUPABASE_URL}/storage/v1/object/public/addons-media/{nome_arquivo}"
    return None

def processar_e_extrair_arquivo(download_url, titulo_mod):
    try:
        print(f"📥 Baixando arquivo original: {titulo_mod}...")
        resp = requests.get(download_url, timeout=30)
        if resp.status_code != 200:
            return None
        
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        
        # 1. Procura se já tem .mcaddon ou .mcpack pronto lá dentro
        for filename in z.namelist():
            fn_lower = filename.lower()
            if fn_lower.endswith(('.mcaddon', '.mcpack', '.mctemplate')):
                print(f"🎯 Arquivo Bedrock direto encontrado: {filename}")
                ext = fn_lower.split('.')[-1]
                conteudo = z.read(filename)
                
                nome_limpo = "".join(c for c in titulo_mod if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_').lower()
                return enviar_arquivo_para_storage(conteudo, f"bot_{nome_limpo}.{ext}")

        # 2. Se não tiver, mas for um zip com pastas do mod, criamos um .mcaddon limpo para o usuário
        print(f"📦 Criando arquivo .mcaddon compatível para '{titulo_mod}'...")
        
        in_memory = io.BytesIO()
        with zipfile.ZipFile(in_memory, 'w', zipfile.ZIP_DEFLATED) as z_out:
            for item in z.infolist():
                # Copia os arquivos de conteúdo do mod para dentro do novo zip limpo
                if not item.is_dir() and '__MACOSX' not in item.filename and not item.filename.endswith('.DS_Store'):
                    z_out.writestr(item.filename, z.read(item.filename))
                    
        in_memory.seek(0)
        nome_limpo = "".join(c for c in titulo_mod if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_').lower()
        return enviar_arquivo_para_storage(in_memory.read(), f"bot_{nome_limpo}.mcaddon")

    except Exception as e:
        print(f"⚠️ Erro ao processar arquivo de {titulo_mod}: {e}")
        
    return None

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
        print(f"🔥 SALVO NO SITE COM SUCESSO: {addon['title']}")
    else:
        dados.pop("downloads", None)
        dados.pop("screenshots", None)
        res_retry = requests.post(url, headers=headers_supabase, json=dados)
        if res_retry.status_code in [200, 201]:
            print(f"✅ SALVO (Modo Simples): {addon['title']}")
        else:
            print(f"❌ ERRO AO SALVAR {addon['title']}: {res.status_code} - {res.text}")

def buscar_curseforge(termo, existentes, coletados):
    if not CURSEFORGE_KEY:
        return

    url = f"https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter={termo}%20bedrock&sortField=2&sortOrder=desc&pageSize=5"
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
                if latest_files:
                    download_url = latest_files[0].get("downloadUrl")
                    
                if not download_url:
                    continue
                
                link_direto_supabase = processar_e_extrair_arquivo(download_url, titulo)
                if not link_direto_supabase:
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
                    "download_url": link_direto_supabase,
                    "downloads": downloads,
                    "screenshots": screenshots
                })
    except Exception as e:
        print(f"Erro CurseForge {termo}: {e}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Seu site já tem {len(existentes)} conteúdos.")
    
    coletados = []
    termos = ["furniture", "weapons"]
    
    for termo in termos:
        print(f"🔍 Pesquisando por '{termo} bedrock'...")
        buscar_curseforge(termo, existentes, coletados)

    if not coletados:
        print("😭 Nenhum mod processado.")
        return

    para_salvar = sorted(coletados, key=lambda x: x['downloads'], reverse=True)[:5]
    para_salvar.sort(key=lambda x: x['downloads'])

    print(f"\n🚀 ENVIANDO {len(para_salvar)} Addons processados para o Supabase...")
    for item in para_salvar:
        salvar_no_supabase(item)

    print("\n🎉 Processo concluído com sucesso total!")

if __name__ == "__main__":
    executar_bot()
