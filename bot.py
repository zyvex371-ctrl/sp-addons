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
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return [item['title'] for item in res.json()]
    return []

def obter_arquivo_bedrock(project_id):
    try:
        url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            versions = res.json()
            for ver in versions:
                for f in ver.get("files", []):
                    filename = f.get("filename", "").lower()
                    if filename.endswith(".mcaddon") or filename.endswith(".mcpack"):
                        return f.get("url")
    except Exception as e:
        print(f"Erro ao obter versão {project_id}: {e}")
    return None

def classificar_categoria(titulo, descricao, tags):
    texto = (titulo + " " + descricao + " " + " ".join(tags)).lower()
    if "texture" in texto or "resource" in texto or "textura" in texto or "pack" in texto:
        return "Texturas"
    return "Add-ons Bedrock"

def buscar_items_api(offset=0):
    url = f'https://api.modrinth.com/v2/search?limit=100&offset={offset}&index=relevance'
    res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
    if res.status_code == 200:
        return res.json().get("hits", [])
    return []

def salvar_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    res = requests.post(url, headers=headers, json=addon)
    if res.status_code in [200, 201]:
        print(f"✅ Cadastrado: {addon['title']} [{addon['category']}]")

def executar_bot():
    existentes = obter_addons_existentes()
    total_no_banco = len(existentes)
    
    # Se tiver menos de 50 itens, faz carga inicial (~30 de cada).
    # Depois, pega 2 de cada a cada 25 minutos.
    limite_addons = 30 if total_no_banco < 50 else 2
    limite_texturas = 30 if total_no_banco < 50 else 2
    
    addons_add = 0
    texturas_add = 0
    
    # Percorre até 500 resultados buscando itens não cadastrados
    for page in range(0, 500, 100):
        if addons_add >= limite_addons and texturas_add >= limite_texturas:
            break
            
        items = buscar_items_api(offset=page)
        if not items:
            break
            
        for item in items:
            if addons_add >= limite_addons and texturas_add >= limite_texturas:
                break
                
            titulo = item.get("title", "").strip()
            if titulo in existentes:
                continue
                
            project_id = item.get("project_id")
            download_url = obter_arquivo_bedrock(project_id)
            
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
                existentes.append(titulo)
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
                existentes.append(titulo)
                texturas_add += 1

    print(f"🎉 Finalizado! Adicionados {addons_add} Addons e {texturas_add} Texturas.")

if __name__ == "__main__":
    executar_bot()
