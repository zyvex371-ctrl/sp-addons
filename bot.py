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
    """Busca os arquivos da versão e garante que seja .mcaddon, .mcpack ou .zip para Bedrock."""
    try:
        url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            versions = res.json()
            for ver in versions:
                for f in ver.get("files", []):
                    filename = f.get("filename", "").lower()
                    # Aceita apenas extensões nativas do Minecraft Bedrock
                    if filename.endswith(".mcaddon") or filename.endswith(".mcpack") or filename.endswith(".zip"):
                        return f.get("url")
    except Exception as e:
        print(f"Erro ao buscar versão para {project_id}: {e}")
    return None

def buscar_novos_addons():
    # Busca focada na categoria Bedrock
    url = 'https://api.modrinth.com/v2/search?limit=20&index=updated'
    res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
    if res.status_code == 200:
        return res.json().get("hits", [])
    return []

def salvar_addon_no_supabase(addon):
    url = f"{SUPABASE_URL}/rest/v1/addons"
    res = requests.post(url, headers=headers, json=addon)
    if res.status_code in [200, 201]:
        print(f"✅ Addon Bedrock salvo: {addon['title']}")

def executar_bot():
    existentes = obter_addons_existentes()
    novos = buscar_novos_addons()
    postados = 0
    
    for item in novos:
        titulo = item.get("title", "").strip()
        if titulo in existentes:
            continue
            
        project_id = item.get("project_id")
        download_url = obter_arquivo_bedrock(project_id)
        
        # Ignora se for arquivo Java (.jar)
        if not download_url:
            continue
            
        novo_addon = {
            "title": titulo,
            "category": "Bedrock",
            "version": "Bedrock Edition",
            "author": item.get("author", "Comunidade"),
            "description": item.get("description", "Add-on para Minecraft Bedrock."),
            "image_url": item.get("icon_url") or "https://via.placeholder.com/400x200",
            "download_url": download_url
        }
        
        salvar_addon_no_supabase(novo_addon)
        postados += 1

    print(f"🎉 Finalizado! {postados} addons Bedrock foram adicionados.")

if __name__ == "__main__":
    executar_bot()
