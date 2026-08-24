import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def obter_addons_existentes():
    url = f"{SUPABASE_URL}/rest/v1/addons?select=title"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return [item['title'].strip().lower() for item in res.json()]
    except Exception as e:
        print(f"Erro ao buscar existentes: {e}")
    return []

def obter_arquivo_download(project_id):
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
        print(f"Erro ao obter versão do projeto {project_id}: {e}")
    return None

def classificar_categoria(titulo, descricao, tags):
    texto = (titulo + " " + descricao + " " + " ".join(tags)).lower()
    if "texture" in texto or "resource" in texto or "textura" in texto or "pack" in texto:
        return "Texturas"
    return "Add-ons Bedrock"

def buscar_items_api(offset=0, query="bedrock"):
    url = f'https://api.modrinth.com/v2/search?query={query}&limit=50&offset={offset}'
    try:
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            return res.json().get("hits", [])
    except Exception as e:
        print(f"Erro na requisição Modrinth: {e}")
    return []

def salvar_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    res = requests.post(url, headers=headers, json=addon)
    if res.status_code in [200, 201]:
        print(f"✅ Cadastrado no site: {addon['title']} [{addon['category']}]")
    else:
        print(f"❌ Erro ao salvar {addon['title']}: {res.status_code} - {res.text}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Itens atualmente cadastrados no banco: {len(existentes)}")
    
    # Meta otimizada: tenta pegar até 5 de cada a cada 27 minutos
    limite_addons = 5
    limite_texturas = 5
    
    addons_add = 0
    texturas_add = 0
    
    termos_busca = ["bedrock", "mcpe", "addon", "texture pack", "resource pack"]
    
    for termo in termos_busca:
        if addons_add >= limite_addons and texturas_add >= limite_texturas:
            break
            
        print(f"🔍 Pesquisando termo: '{termo}'...")
        
        for page in range(0, 400, 50):
            if addons_add >= limite_addons and texturas_add >= limite_texturas:
                break
                
            items = buscar_items_api(offset=page, query=termo)
            if not items:
                break
                
            for item in items:
                if addons_add >= limite_addons and texturas_add >= limite_texturas:
                    break
                    
                titulo = item.get("title", "").strip()
                if not titulo or titulo.lower() in existentes:
                    continue
                    
                project_id = item.get("project_id")
                download_url = obter_arquivo_download(project_id)
                
                if not download_url:
                    continue
                    
                desc = item.get("description", "Conteúdo para Minecraft Bedrock.")
                tags = item.get("categories", [])
                cat = classificar_categoria(titulo, desc, tags)
                
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

    print(f"🎉 Finalizado! Adicionados {addons_add} Addons e {texturas_add} Texturas nesta rodada.")

if __name__ == "__main__":
    executar_bot()
