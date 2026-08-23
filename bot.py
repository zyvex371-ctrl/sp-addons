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

novo_addon = {
    "title": "Addon de Teste SP",
    "category": "Geral",
    "version": "1.0",
    "author": "SP Addons Bot",
    "description": "Addon enviado automaticamente pelo robô do GitHub!",
    "image_url": "https://via.placeholder.com/400x200",
    "download_url": "https://example.com"
}

url = f"{SUPABASE_URL}/rest/v1/addons"
response = requests.post(url, headers=headers, json=novo_addon)

if response.status_code in [200, 201]:
    print("✅ Addon enviado com sucesso para o Supabase!")
else:
    print(f"❌ Erro ao enviar: {response.status_code} - {response.text}")

