# -*- coding: utf-8 -*-
import sys
import os
import re
from datetime import datetime
from urllib.parse import urljoin
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

SMTP_SERVER = (os.getenv("SMTP_SERVER") or default_server).strip()
SMTP_PORT = int(os.getenv("SMTP_PORT") or default_port)

BASE_URL = "https://www.comprasparaguai.com.br"

def normalizar_preco(valor):
    texto = valor.replace("US$", "").replace("R$", "").replace("\xa0", " ").strip()
    texto = re.sub(r"[^0-9,.]", "", texto)
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None

def extrair_ofertas_produto(scraper, url_produto, modelo, data_coleta):
    resposta = scraper.get(url_produto, timeout=20)
    if resposta.status_code != 200:
        print(f"[!] Detalhes indisponíveis (Status: {resposta.status_code}): {url_produto}")
        return []

    sopa = BeautifulSoup(resposta.text, "html.parser")
    ofertas = []
    for item in sopa.select("#container-ofertas div.promocao-produtos-item"):
        nome_elem = item.select_one(".promocao-item-nome")
        nome_produto = nome_elem.get_text(" ", strip=True) if nome_elem else modelo
        if "iphone 17 pro max" not in nome_produto.lower():
            continue
        codigo_elem = item.select_one(".promocao-item-caracteristicas")
        codigo = codigo_elem.get_text(" ", strip=True).replace("Código:", "").strip() if codigo_elem else ""

        preco_usd_elem = item.select_one(".promocao-item-preco-oferta strong")
        preco_brl_elem = item.select_one(".promocao-item-preco-text")
        preco_usd = normalizar_preco(preco_usd_elem.get_text(" ", strip=True) if preco_usd_elem else "")
        preco_brl = normalizar_preco(preco_brl_elem.get_text(" ", strip=True) if preco_brl_elem else "")

        loja_elem = item.select_one("img.store-image")
        loja = (loja_elem.get("alt") or loja_elem.get("title") or "").strip() if loja_elem else ""
        if not loja:
            advertiser = re.search(r"['\"]advertiser['\"]\s*:\s*['\"]([^'\"]+)", str(item))
            loja = advertiser.group(1).strip() if advertiser else "Loja não identificada"

        link_loja_elem = item.select_one("img.store-image")
        link_loja = ""
        if link_loja_elem and link_loja_elem.parent and link_loja_elem.parent.name == "a":
            link_loja = urljoin(BASE_URL, link_loja_elem.parent.get("href", ""))
        link_produto_elem = item.select_one(".promocao-item-nome a")

        ofertas.append({
            "Data": data_coleta,
            "Modelo": modelo,
            "Produto": nome_produto,
            "Loja": loja,
            "Preco_USD": preco_usd,
            "Preco_BRL": preco_brl,
            "Codigo": codigo,
            "Link_Produto": urljoin(BASE_URL, link_produto_elem.get("href", "")) if link_produto_elem else url_produto,
            "Link_Loja": link_loja,
        })
    return ofertas

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
        data_coleta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in itens:
            nome_elem = item.find("div", class_="promocao-item-nome")
            nome = nome_elem.get_text(strip=True) if nome_elem else "Modelo não identificado"
            link_elem = nome_elem.find("a") if nome_elem else None
            link_produto = urljoin(BASE_URL, link_elem.get("href", "")) if link_elem else ""
            if link_produto:
                produtos.extend(extrair_ofertas_produto(scraper, link_produto, nome, data_coleta))
            
        return produtos

    except Exception as e:
        print(f"[X] Erro crítico no scraping: {e}")
        return []

def preparar_relatorio_256gb(df):
    produtos = df["Produto"].fillna("")
    filtro_256gb = produtos.str.contains(r"\b256\s*GB\b", case=False, regex=True)
    filtro_a3526 = produtos.str.contains(r"\bA3526\b", case=False, regex=True)
    filtro = filtro_256gb & filtro_a3526
    relatorio = df.loc[filtro].copy()
    relatorio["Preco_BRL"] = pd.to_numeric(relatorio["Preco_BRL"], errors="coerce")
    relatorio["Preco_USD"] = pd.to_numeric(relatorio["Preco_USD"], errors="coerce")
    lojas_normalizadas = relatorio["Loja"].fillna("").str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    loja_preferida = lojas_normalizadas.str.contains(r"nissei|cellshop", regex=True)
    relatorio["Preferencia_Loja"] = loja_preferida.map({True: "Preferida", False: "Demais lojas"})
    relatorio["_Ordem_Preferencia"] = (~loja_preferida).astype(int)
    relatorio = relatorio.sort_values(
        ["_Ordem_Preferencia", "Preco_BRL", "Preco_USD", "Loja"],
        ascending=[True, True, True, True],
        na_position="last",
        kind="mergesort",
    ).drop(columns="_Ordem_Preferencia")
    return relatorio.reset_index(drop=True)

def enviar_relatorio_email(df, caminho_csv=None):
    df = preparar_relatorio_256gb(df)
    if df.empty:
        print("[!] Nenhuma oferta do iPhone 17 Pro Max A3526 de 256 GB para incluir no relatório.")
        return False

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

    # Prioriza o preço e a loja na tabela do e-mail; o CSV mantém todos os campos.
    colunas_email = ["Preferencia_Loja", "Preco_BRL", "Loja", "Produto", "Preco_USD"]
    tabela_email = df[colunas_email].copy()
    formatadores = {
        "Preco_BRL": lambda valor: f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "Preco_USD": lambda valor: f"US$ {valor:,.2f}",
    }
    tabela_html = tabela_email.to_html(
        index=False,
        border=0,
        classes="tabela-dados",
        formatters=formatadores,
    )
    
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
            <h2>📱 iPhone 17 Pro Max A3526 - 256 GB - Paraguai</h2>
            <p>Relatório gerado automaticamente em <strong>{datetime.now().strftime('%d/%m/%Y às %H:%M')}</strong>.</p>
            <p>Nissei e Cellshop aparecem primeiro; cada grupo está ordenado do menor para o maior preço em reais.</p>
            <p>A preferência organiza a visualização e não confirma autenticidade, procedência ou condição do aparelho. Confirme se é novo ou Swap diretamente com a loja.</p>
            <span class="badge">Total de Ofertas: {len(df)}</span>
            
            {tabela_html}
            
            <p class="footer">
                Fonte: Compras Paraguai (Ciudad del Este)<br>
                O CSV com as ofertas do modelo A3526 de 256 GB, a preferência de loja e os links está anexado.
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

def salvar_historico(df, caminho_csv):
    colunas = ["Data", "Modelo", "Produto", "Loja", "Preco_USD", "Preco_BRL", "Codigo", "Link_Produto", "Link_Loja"]
    df = df.reindex(columns=colunas)
    existe = os.path.exists(caminho_csv) and os.path.getsize(caminho_csv) > 0
    df.to_csv(caminho_csv, mode="a", header=not existe, index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    termo = "iphone 17 pro max"
    dados = raspar_precos_paraguai(termo)
    
    if dados:
        df = pd.DataFrame(dados)
        print(f"\n[+] SUCESSO! Encontrados {len(df)} modelos.\n")
        
        # Salva o arquivo CSV no Desktop
        desktop = obter_caminho_desktop()
        caminho_csv = os.path.join(desktop, "historico_precos_iphone.csv")
        salvar_historico(df, caminho_csv)
        print(f"[+] Histórico atualizado salvo em:\n    {caminho_csv}")
        
        # O histórico mantém todas as ofertas; o relatório destaca Nissei e Cellshop primeiro.
        df_relatorio = preparar_relatorio_256gb(df)
        caminho_relatorio_csv = os.path.join(desktop, "relatorio_iphone_17_pro_max_256gb.csv")
        df_relatorio.to_csv(caminho_relatorio_csv, index=False, encoding="utf-8-sig")

        # Dispara o envio por e-mail com a lista filtrada e ordenada.
        if not enviar_relatorio_email(df_relatorio, caminho_relatorio_csv):
            raise SystemExit(1)
    else:
        print("[!] Nenhum resultado foi extraído.")
        raise SystemExit(1)
