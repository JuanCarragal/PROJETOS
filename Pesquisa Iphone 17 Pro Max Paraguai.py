# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env)
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Garante suporte a caracteres especiais no terminal Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configurações de E-mail
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "").strip()
EMAIL_SENHA = os.getenv("EMAIL_SENHA", "").strip().replace(" ", "")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO", "carragal@hotmail.com").strip()

# Se o remetente for Gmail, assegura servidor e porta do Gmail por padrão
default_server = "smtp.gmail.com" if "gmail.com" in EMAIL_REMETENTE.lower() else "smtp-mail.outlook.com"
default_port = 465 if "gmail.com" in EMAIL_REMETENTE.lower() else 587

SMTP_SERVER = os.getenv("SMTP_SERVER", default_server).strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", default_port))

def raspar_precos_paraguai(termo_busca="iphone 17 pro max"):
    url_alvo = f"https://www.comprasparaguai.com.br/busca/?q={termo_busca.replace(' ', '+')}"
    print(f"[*] Acessando portal: {url_alvo}")
    
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True
        }
    )
    
    try:
        resposta = scraper.get(url_alvo, timeout=15)
        
        if resposta.status_code != 200:
            print(f"[X] O site recusou a conexão (Status: {resposta.status_code})")
            return []
            
        print(f"[+] Conexão liberada (Status {resposta.status_code})! Analisando o HTML...")
        sopa = BeautifulSoup(resposta.text, "html.parser")
        
        itens = sopa.find_all("div", class_="promocao-produtos-item")
        if not itens:
            print("[!] Nenhum item encontrado com a classe 'promocao-produtos-item'.")
            return []
            
        produtos = []
        for item in itens:
            nome_elem = item.find("div", class_="promocao-item-nome")
            nome = nome_elem.get_text(strip=True) if nome_elem else "Modelo não identificado"
            
            preco_elem = item.find("div", class_="price-model")
            preco_usd_raw = preco_elem.find("span").get_text(strip=True) if (preco_elem and preco_elem.find("span")) else ""
            preco_brl_raw = item.find("div", class_="promocao-item-preco-text").get_text(strip=True) if item.find("div", class_="promocao-item-preco-text") else ""
            
            # Limpeza de caracteres
            preco_usd = preco_usd_raw.replace("US$", "").replace("U$", "").replace("\xa0", " ").strip()
            preco_brl = preco_brl_raw.replace("R$", "").replace("\xa0", " ").strip()
            
            produtos.append({
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Modelo": nome,
                "Preco_USD": preco_usd,
                "Preco_BRL": preco_brl
            })
            
        return produtos

    except Exception as e:
        print(f"[X] Erro crítico no scraping: {e}")
        return []

def enviar_relatorio_email(df, caminho_csv=None):
    if not EMAIL_SENHA or EMAIL_SENHA == "sua_senha_ou_senha_de_app_aqui":
        print("\n[!] AVISO: Senha de e-mail não configurada no arquivo .env.")
        print(f"    Para ativar o envio para {EMAIL_DESTINO}, defina EMAIL_SENHA no arquivo .env")
        return False

    print(f"[*] Preparando envio de e-mail para: {EMAIL_DESTINO} via {SMTP_SERVER}...")
    
    msg = MIMEMultipart()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    data_formatada = datetime.now().strftime("%d/%m/%Y")
    msg["Subject"] = f"📊 Relatório Diário - iPhone no Paraguai ({data_formatada})"

    # Gera tabela HTML estilizada
    tabela_html = df.to_html(index=False, border=0, classes="tabela-dados")
    
    corpo_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7f9; margin: 0; padding: 20px; }}
            .card {{ background-color: #ffffff; max-width: 650px; margin: 0 auto; padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            h2 {{ color: #1e293b; margin-top: 0; }}
            p {{ color: #475569; font-size: 14px; line-height: 1.5; }}
            .tabela-dados {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }}
            .tabela-dados th {{ background-color: #0f172a; color: #ffffff; text-align: left; padding: 10px; border-radius: 4px; }}
            .tabela-dados td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; color: #334155; }}
            .tabela-dados tr:nth-child(even) {{ background-color: #f8fafc; }}
            .footer {{ margin-top: 24px; font-size: 12px; color: #94a3b8; text-align: center; }}
            .badge {{ display: inline-block; padding: 4px 8px; border-radius: 6px; background-color: #e0f2fe; color: #0369a1; font-weight: 600; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>📱 Monitoramento de Preços - Paraguai</h2>
            <p>Relatório gerado automaticamente em <strong>{datetime.now().strftime('%d/%m/%Y às %H:%M')}</strong>.</p>
            <span class="badge">Total de Modelos: {len(df)}</span>
            
            {tabela_html}
            
            <p class="footer">
                Fonte: Compras Paraguai (Ciudad del Este)<br>
                A planilha completa (.csv) foi anexada a este e-mail.
            </p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))
    
    # Anexa o CSV se existir
    if caminho_csv and os.path.exists(caminho_csv):
        try:
            with open(caminho_csv, "rb") as anexo:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(anexo.read())
            encoders.encode_base64(part)
            nome_arquivo = os.path.basename(caminho_csv)
            part.add_header("Content-Disposition", f"attachment; filename={nome_arquivo}")
            msg.attach(part)
        except Exception as e:
            print(f"[!] Erro ao anexar arquivo CSV: {e}")

    try:
        if SMTP_PORT == 465:
            servidor = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20)
        else:
            servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
            servidor.ehlo()
            servidor.starttls()
            servidor.ehlo()
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
        servidor.sendmail(EMAIL_REMETENTE, EMAIL_DESTINO, msg.as_string())
        servidor.quit()
        print(f"[+] E-mail enviado com sucesso para {EMAIL_DESTINO}!")
        return True
    except Exception as e:
        print(f"[X] Falha no envio do e-mail: {e}")
        return False

def obter_caminho_desktop():
    desktop = os.path.expanduser(r"~\OneDrive\Área de Trabalho")
    if not os.path.exists(desktop):
        desktop = os.path.expanduser(r"~\Desktop")
    if not os.path.exists(desktop):
        desktop = os.getcwd()
    return desktop

if __name__ == "__main__":
    termo = "iphone 17 pro max"
    dados = raspar_precos_paraguai(termo)
    
    if dados:
        df = pd.DataFrame(dados)
        print(f"\n[+] SUCESSO! Encontrados {len(df)} modelos.\n")
        
        # Salva o arquivo CSV no Desktop
        desktop = obter_caminho_desktop()
        caminho_csv = os.path.join(desktop, "historico_iphone_paraguai.csv")
        df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        print(f"[+] Planilha atualizada salva em:\n    {caminho_csv}")
        
        # Dispara o envio por e-mail
        if not enviar_relatorio_email(df, caminho_csv):
            raise SystemExit(1)
    else:
        print("[!] Nenhum resultado foi extraído.")
        raise SystemExit(1)
