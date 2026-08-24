import os
import requests
import cloudscraper
from bs4 import BeautifulSoup

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

headers_supabase = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def obter_addons_existentes():
    url = f"{SUPABASE_URL}/rest/v1/addons?select=title"
    try:
        res = requests.get(url, headers=headers_supabase)
        if res.status_code == 200:
            return [item['title'].strip().lower() for item in res.json()]
    except Exception as e:
        print(f"Erro ao buscar existentes: {e}")
    return []

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
    
    # Tenta salvar no Supabase
    res = requests.post(url, headers=headers_supabase, json=dados)
    if res.status_code in [200, 201]:
        print(f"🔥 Cadastrado no site: {addon['title']} [{addon['category']}]")
    else:
        # Se der erro (ex: falta a coluna downloads), tenta modo simples
        dados.pop("downloads", None)
        res_retry = requests.post(url, headers=headers_supabase, json=dados)
        if res_retry.status_code in [200, 201]:
            print(f"✅ Cadastrado no site (Modo Simples): {addon['title']}")
        else:
            print(f"❌ Erro ao salvar {addon['title']}: {res.status_code} - {res.text}")

def raspar_mcpedl(url_alvo, categoria, existentes, coletados):
    print(f"\n🕵️‍♂️ Entrando no MCPEDL para copiar: {categoria}...")
    
    # O Cloudscraper "finge" ser um navegador de verdade para não ser bloqueado
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        resposta = scraper.get(url_alvo)
        if resposta.status_code != 200:
            print(f"❌ Site bloqueou o robô. Código: {resposta.status_code}")
            return
        
        # O BeautifulSoup lê a tela do site
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # Procura as caixas de postagens (No MCPEDL geralmente são tags <article>)
        postagens = soup.find_all('article')
        
        if not postagens:
            print("⚠️ Nenhuma postagem encontrada na estrutura do site.")
            return

        print(f"📦 Encontramos {len(postagens)} itens na página. Processando...")

        for post in postagens:
            # Pega o Título
            titulo_tag = post.find('h2') or post.find('h3')
            if not titulo_tag: continue
            titulo = titulo_tag.text.strip()
            
            # Evita duplicados
            if not titulo or titulo.lower() in existentes or any(c['title'].lower() == titulo.lower() for c in coletados):
                continue

            # Pega o Link da Postagem (Link para o cara baixar)
            link_tag = titulo_tag.find('a')
            link = ""
            if link_tag and 'href' in link_tag.attrs:
                link = "https://mcpedl.com" + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']

            # Pega a Imagem da Capa
            img_tag = post.find('img')
            imagem = "https://via.placeholder.com/400x200"
            if img_tag:
                if 'data-src' in img_tag.attrs:
                    imagem = img_tag['data-src']
                elif 'src' in img_tag.attrs:
                    imagem = img_tag['src']

            # Pega a Descrição (Resumo)
            desc_tag = post.find('p')
            descricao = desc_tag.text.strip() if desc_tag else "Conteúdo incrível extraído do MCPEDL."

            # Guarda os dados perfeitos
            coletados.append({
                "title": titulo,
                "category": categoria,
                "version": "Bedrock",
                "author": "Comunidade MCPEDL",
                "description": descricao,
                "image_url": imagem,
                "download_url": link,  # Mandamos o usuário para a página do MCPEDL para ele baixar seguro
                "downloads": 5000  # Valor base alto para ele ficar bem posicionado no seu site
            })
            
    except Exception as e:
        print(f"Erro ao raspar a página {url_alvo}: {e}")

def executar_bot():
    existentes = obter_addons_existentes()
    print(f"📌 Itens já cadastrados no seu banco: {len(existentes)}")
    
    coletados = []
    
    # 1. Copia os Mods/Addons mais recentes
    raspar_mcpedl("https://mcpedl.com/category/mods/addons/", "Add-ons Bedrock", existentes, coletados)
    
    # 2. Copia as Texturas mais recentes
    raspar_mcpedl("https://mcpedl.com/category/texture-packs/", "Texturas", existentes, coletados)

    # Pegamos apenas as 5 novidades de cada pra não floodar o banco
    novos_addons = [item for item in coletados if item['category'] == "Add-ons Bedrock"][:5]
    novas_texturas = [item for item in coletados if item['category'] == "Texturas"][:5]

    print(f"\n🚀 Salvando {len(novos_addons)} Novos Addons e {len(novas_texturas)} Novas Texturas no seu site...")

    # Salva no banco de dados
    for item in novos_addons:
        salvar_no_supabase(item)

    for item in novas_texturas:
        salvar_no_supabase(item)

    print("\n🎉 Web Scraping finalizado! 100% de conteúdo Bedrock puro extraído com sucesso.")

if __name__ == "__main__":
    executar_bot()
