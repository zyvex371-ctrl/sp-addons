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

def obter_arquivo_bedrock_valido(project_id):
    """Filtra EXCLUSIVAMENTE arquivos .mcaddon e .mcpack para abrir direto no Minecraft."""
    try:
        url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            versions = res.json()
            for ver in versions:
                for f in ver.get("files", []):
                    filename = f.get("filename", "").lower()
                    if filename.endswith(".mcaddon") or filename.endswith(".mcpack"):
                        return f.get("url"), filename
    except Exception as e:
        print(f"Erro no projeto {project_id}: {e}")
    return None, None

def classificar_categoria(titulo, descricao, tags):
    """Classifica automaticamente entre Add-ons, Texturas e Mapas."""
    texto = (titulo + " " + descricao + " " + " ".join(tags)).lower()
    if "texture" in texto or "resource" in texto or "textura" in texto:
        return "Texturas"
    elif "map" in texto or "world" in texto or "mapa" in texto:
        return "Mapas"
    else:
        return "Add-ons Bedrock"

def buscar_novos_addons():
    url = 'https://api.modrinth.com/v2/search?limit=30&index=updated'
    res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
    if res.status_code == 200:
        return res.json().get("hits", [])
    return []

def salvar_addon_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    res = requests.post(url, headers=headers, json=addon)
    if res.status_code in [200, 201]:
        print(f"✅ Bedrock válido salvo: {addon['title']} [{addon['category']}]")

def executar_bot():
    existentes = obter_addons_existentes()
    novos = buscar_novos_addons()
    postados = 0
    
    for item in novos:
        titulo = item.get("title", "").strip()
        if titulo in existentes:
            continue
            
        project_id = item.get("project_id")
        download_url, filename = obter_arquivo_bedrock_valido(project_id)
        
        # Descarta arquivos incompatíveis (.jar, .zip, etc)
        if not download_url:
            continue
            
        desc = item.get("description", "Conteúdo incrível para Minecraft Bedrock.")
        tags = item.get("categories", [])
        categoria = classificar_categoria(titulo, desc, tags)
        
        novo_addon = {
            "title": titulo,
            "category": categoria,
            "version": "Bedrock Edition",
            "author": item.get("author", "Comunidade"),
            "description": desc,
            "image_url": item.get("icon_url") or "https://via.placeholder.com/400x200",
            "download_url": download_url
        }
        
        salvar_addon_no_supabase(novo_addon)
        postados += 1

    print(f"🎉 Finalizado! {postados} itens Bedrock (.mcaddon / .mcpack) adicionados.")

if __name__ == "__main__":
    executar_bot()
