"""
Executa após 'docker compose up -d':
  - Cria a instância no Evolution API
  - Configura o webhook apontando para o FastAPI local
  - Imprime o QR Code para escanear no WhatsApp
"""

import sys
import time
import httpx

EVOLUTION_URL = "http://localhost:8080"
API_KEY = "evfit_secret_key_2026"
INSTANCE = "evolutionfit"
WEBHOOK_URL = "http://host.docker.internal:8000/webhook/whatsapp"

HEADERS = {"apikey": API_KEY, "Content-Type": "application/json"}


def wait_for_api(timeout=60):
    print("Aguardando Evolution API iniciar...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{EVOLUTION_URL}/", timeout=3)
            if r.status_code < 500:
                print("Evolution API pronta.")
                return True
        except Exception:
            pass
        time.sleep(3)
    print("Timeout: Evolution API não respondeu.")
    return False


def create_instance():
    print(f"Criando instância '{INSTANCE}'...")
    r = httpx.post(
        f"{EVOLUTION_URL}/instance/create",
        headers=HEADERS,
        json={
            "instanceName": INSTANCE,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        },
    )
    if r.status_code in (200, 201):
        print("Instância criada com sucesso.")
        return True
    if r.status_code == 403 and "already" in r.text.lower():
        print("Instância já existe, continuando...")
        return True
    print(f"Erro ao criar instância: {r.status_code} {r.text}")
    return False


def set_webhook():
    print("Configurando webhook...")
    r = httpx.post(
        f"{EVOLUTION_URL}/webhook/set/{INSTANCE}",
        headers=HEADERS,
        json={
            "url": WEBHOOK_URL,
            "webhook_by_events": False,
            "webhook_base64": False,
            "events": [
                "MESSAGES_UPSERT",
                "CONNECTION_UPDATE",
            ],
        },
    )
    if r.status_code in (200, 201):
        print(f"Webhook configurado: {WEBHOOK_URL}")
        return True
    print(f"Erro ao configurar webhook: {r.status_code} {r.text}")
    return False


def print_qrcode():
    print("\nBuscando QR Code...")
    for attempt in range(10):
        r = httpx.get(
            f"{EVOLUTION_URL}/instance/connect/{INSTANCE}",
            headers=HEADERS,
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("base64"):
                print("\nQR Code gerado! Acesse no navegador para escanear:")
                print(f"  http://localhost:8080/instance/connect/{INSTANCE}")
                print("\nOu use a rota da API diretamente:")
                print(f"  GET http://localhost:8080/instance/connect/{INSTANCE}")
                print(f"  Header: apikey: {API_KEY}")
                return True
            state = data.get("instance", {}).get("state", "")
            if state == "open":
                print("WhatsApp já está conectado!")
                return True
        time.sleep(3)
    print("QR Code não disponível ainda. Tente acessar manualmente:")
    print(f"  GET http://localhost:8080/instance/connect/{INSTANCE}")
    return False


if __name__ == "__main__":
    if not wait_for_api():
        sys.exit(1)
    if not create_instance():
        sys.exit(1)
    if not set_webhook():
        sys.exit(1)
    print_qrcode()
    print("\nSetup concluido!")
    print(f"  Evolution API: {EVOLUTION_URL}")
    print(f"  Instancia:     {INSTANCE}")
    print(f"  Webhook:       {WEBHOOK_URL}")
    print(f"  API Key:       {API_KEY}")
