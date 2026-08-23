import os
import requests

# Variáveis do Supabase configuradas nos Secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def obter_addons_existentes():
    """Busca no Supabase os títulos já cadastrados para evitar duplicados."""
    url = f"{SUPABASE_URL}/rest/v1/addons?select=title"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return [item['title'] for item in res.json()]
    return []

def obter_link_download_direto(project_id):
    """Acessa os arquivos da versão e pega a URL de download direto do arquivo real (.zip, .jar, .mcpack)."""
    try:
        url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
        if res.status_code == 200:
            versions = res.json()
            if versions and len(versions) > 0:
                files = versions[0].get("files", [])
                if files and len(files) > 0:
                    # Retorna o link direto do arquivo físico no servidor CDN
                    return files[0].get("url")
    except Exception as e:
        print(f"Erro ao buscar link direto do projeto {project_id}: {e}")
    return None

def buscar_novos_addons():
    """Busca os addons e mods na API do Modrinth."""
    url = "https://api.modrinth.com/v2/search?limit=10&index=updated"
    res = requests.get(url, headers={"User-Agent": "SPAddonsBot/1.0"})
    if res.status_code == 200:
        return res.json().get("hits", [])
    return []

def salvar_addon_no_supabase(addon):
    """Envia o addon com o arquivo de download direto para o banco de dados."""
    url = f"{SUPABASE_URL}/rest/v1/addons"
    res = requests.post(url, headers=headers, json=addon)
    if res.status_code in [200, 201]:
        print(f"✅ Postado com download direto: {addon['title']}")
    else:
        print(f"❌ Erro ao postar {addon['title']}: {res.status_code} - {res.text}")

def executar_bot():
    print("🔍 Verificando banco de dados...")
    existentes = obter_addons_existentes()
    
    print("🌐 Buscando lançamentos na internet...")
    novos = buscar_novos_addons()
    
    postados = 0
    for item in novos:
        titulo = item.get("title", "").strip()
        
        if titulo in existentes:
            continue
            
        project_id = item.get("project_id")
        
        # Pega a URL DIRETA do arquivo do addon
        download_url = obter_link_download_direto(project_id)
        
        # Se não houver arquivo direto disponível, pula para o próximo
        if not download_url:
            continue
        
        novo_addon = {
            "title": titulo,
            "category": item.get("categories", ["Geral"])[0].capitalize() if item.get("categories") else "Geral",
            "version": "Mais recente",
            "author": item.get("author", "Comunidade"),
            "description": item.get("description", "Sem descrição disponível."),
            "image_url": item.get("icon_url") or "https://via.placeholder.com/400x200",
            "download_url": download_url  # URL direta do arquivo (cdn.modrinth.com/...)
        }
        
        salvar_addon_no_supabase(novo_addon)
        postados += 1

    print(f"🎉 Finalizado! {postados} novos addons com download direto foram cadastrados.")

if __name__ == "__main__":
    executar_bot()
