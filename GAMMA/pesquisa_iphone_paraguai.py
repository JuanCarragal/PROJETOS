# -*- coding: utf-8 -*-
import sys
import os
import re
import traceback
import json
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from datetime import datetime
import cloudscraper
from openpyxl.utils import get_column_letter
import mimetypes
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
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
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO", "").strip() or "carragal@hotmail.com"

# Se o remetente for Gmail, assegura servidor e porta do Gmail por padrão
default_server = "smtp.gmail.com" if "gmail.com" in EMAIL_REMETENTE.lower() else "smtp-mail.outlook.com"
default_port = 465 if "gmail.com" in EMAIL_REMETENTE.lower() else 587

SMTP_SERVER = os.getenv("SMTP_SERVER", "").strip() or default_server
SMTP_PORT = int(os.getenv("SMTP_PORT", "") or default_port)

def obter_cotacao_dolar(data_referencia=None):
    data_referencia = data_referencia or datetime.now().date()
    base_url = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"

    for dias_atras in range(11):
        data_consulta = data_referencia - timedelta(days=dias_atras)
        data_parametro = data_consulta.strftime("%m-%d-%Y")
        url = (
            f"{base_url}CotacaoDolarDia(dataCotacao=@dataCotacao)?"
            f"@dataCotacao='{data_parametro}'&$top=100&$format=json"
        )
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=10) as resposta:
                registros = json.load(resposta).get("value", [])
        except Exception as e:
            print(f"[!] Não foi possível consultar a cotação PTAX no BCB: {e}")
            return None

        if registros:
            registro = max(registros, key=lambda item: item["dataHoraCotacao"])
            return {
                "valor": float(registro["cotacaoVenda"]),
                "data": registro["dataHoraCotacao"][:10],
            }

    print("[!] Nenhuma cotação PTAX encontrada nos últimos 10 dias.")
    return None

def _criar_scraper():
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )

def _extrair_ofertas_produto(scraper, url_modelo):
    """Acessa a página de um modelo e retorna lista de (loja, nome_variante, preco_brl)."""
    ofertas = []
    try:
        resp = scraper.get(url_modelo, timeout=15)
        if resp.status_code != 200:
            return ofertas
        sopa = BeautifulSoup(resp.text, "html.parser")
        itens = sopa.find_all("div", class_="promocao-produtos-item")
        for item in itens:
            # Nome da variante
            nome_elem = item.find("div", class_="promocao-item-nome")
            nome = nome_elem.get_text(strip=True) if nome_elem else "?"

            # Loja via atributo onclick do gtag
            loja = "?"
            for tag in item.find_all(attrs={"onclick": True}):
                m = re.search(r"'advertiser'\s*:\s*'([^']+)'", tag["onclick"])
                if m:
                    loja = m.group(1)
                    break

            # Preço em BRL
            preco_brl_elem = item.find("div", class_="promocao-item-preco-text")
            preco_brl = preco_brl_elem.get_text(strip=True).replace("R$", "").replace("\xa0", " ").strip() if preco_brl_elem else "N/D"

            # Preço em USD (nem sempre disponível na página de produto)
            preco_elem = item.find("div", class_="price-model")
            preco_usd = ""
            if preco_elem and preco_elem.find("span"):
                preco_usd = preco_elem.find("span").get_text(strip=True).replace("US$", "").replace("U$", "").replace("\xa0", " ").strip()

            ofertas.append({"loja": loja, "nome": nome, "preco_usd": preco_usd, "preco_brl": preco_brl})
    except Exception:
        pass
    return ofertas

def raspar_precos_paraguai(termo_busca="iphone 17 pro max"):
    url_busca = f"https://www.comprasparaguai.com.br/busca/?q={termo_busca.replace(' ', '+')}"
    print(f"[*] Acessando busca: {url_busca}")

    scraper = _criar_scraper()

    try:
        resposta = scraper.get(url_busca, timeout=15)
        if resposta.status_code != 200:
            print(f"[X] O site recusou a conexão (Status: {resposta.status_code})")
            return []

        print(f"[+] Conexão liberada! Coletando modelos...")
        sopa = BeautifulSoup(resposta.text, "html.parser")

        # Coleta links únicos de modelos da página de busca
        links_modelos = {}
        for item in sopa.find_all("div", class_="promocao-produtos-item"):
            nome_elem = item.find("div", class_="promocao-item-nome")
            link_tag = nome_elem.find("a") if nome_elem else None
            if link_tag and link_tag.get("href"):
                nome_modelo = nome_elem.get_text(strip=True)
                href = link_tag["href"]
                if href not in links_modelos:
                    links_modelos[href] = nome_modelo

        print(f"[+] {len(links_modelos)} modelos encontrados. Buscando ofertas por loja...")

        produtos = []
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")

        for href, nome_modelo in links_modelos.items():
            url_modelo = f"https://www.comprasparaguai.com.br{href}" if href.startswith("/") else href
            print(f"   -> {nome_modelo[:50]}")
            ofertas = _extrair_ofertas_produto(scraper, url_modelo)
            for o in ofertas:
                produtos.append({
                    "Data": data_atual,
                    "Modelo": nome_modelo,
                    "Loja": o["loja"],
                    "Variante": o["nome"],
                    "Preco_USD": o["preco_usd"],
                    "Preco_BRL": o["preco_brl"],
                })

        return produtos

    except Exception as e:
        print(f"[X] Erro crítico no scraping: {e}")
        raise RuntimeError(f"Erro crítico no scraping: {e}") from e

def salvar_relatorio_excel(df, caminho_xlsx, cotacao_dolar=None):
    with pd.ExcelWriter(caminho_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Preços do dia", startrow=2)
        planilha = writer.sheets["Preços do dia"]
        ultima_coluna = get_column_letter(len(df.columns))
        planilha.merge_cells(f"A1:{ultima_coluna}1")
        celula_cotacao = planilha["A1"]
        if cotacao_dolar:
            valor_formatado = f"{cotacao_dolar['valor']:.4f}".replace(".", ",")
            data_formatada = datetime.strptime(cotacao_dolar["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
            celula_cotacao.value = f"Dólar PTAX venda: R$ {valor_formatado} | Cotação de {data_formatada} | Banco Central do Brasil"
        else:
            celula_cotacao.value = "Dólar PTAX venda: indisponível | Banco Central do Brasil"
        celula_cotacao.font = Font(bold=True, color="FFFFFF", size=12)
        celula_cotacao.fill = PatternFill(fill_type="solid", fgColor="17324D")
        celula_cotacao.alignment = Alignment(vertical="center", horizontal="left")
        planilha.row_dimensions[1].height = 30
        planilha.row_dimensions[2].height = 8
        planilha.freeze_panes = "A4"
        planilha.auto_filter.ref = f"A3:{ultima_coluna}{planilha.max_row}"

        for celula in planilha[3]:
            celula.font = Font(bold=True, color="FFFFFF")
            celula.fill = PatternFill(fill_type="solid", fgColor="17324D")
            celula.alignment = Alignment(vertical="center", wrap_text=True)
        planilha.row_dimensions[3].height = 24

        for indice_coluna, coluna in enumerate(planilha.columns, start=1):
            largura = max(len(str(celula.value or "")) for celula in coluna)
            planilha.column_dimensions[get_column_letter(indice_coluna)].width = min(max(largura + 2, 12), 42)
            for celula in coluna[3:]:
                celula.alignment = Alignment(vertical="top")

        if "Cotacao_USD_BRL" in df.columns:
            coluna_cotacao = df.columns.get_loc("Cotacao_USD_BRL") + 1
            for linha in range(4, planilha.max_row + 1):
                planilha.cell(linha, coluna_cotacao).number_format = '"R$ "0.0000'

def enviar_relatorio_email(df, caminho_csv=None, anexos_extras=None, caminho_xlsx=None):
    if not EMAIL_SENHA or EMAIL_SENHA == "sua_senha_ou_senha_de_app_aqui":
        print("\n[!] AVISO: Senha de e-mail não configurada no arquivo .env.")
        print(f"    Para ativar o envio para {EMAIL_DESTINO}, defina EMAIL_SENHA no arquivo .env")
        return False

    print(f"[*] Preparando envio de e-mail para: {EMAIL_DESTINO} via {SMTP_SERVER}...")
    
    msg = MIMEMultipart()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    data_formatada = datetime.now().strftime("%d/%m/%Y")
    
    eh_sexta = datetime.now().weekday() == 4
    assunto_extra = " [EDIÇÃO SEMANAL + INFOGRÁFICO]" if eh_sexta else ""
    msg["Subject"] = f"📊 Relatório Diário - iPhone no Paraguai ({data_formatada}){assunto_extra}"

    # Gera tabela HTML estilizada
    tabela_html = df.to_html(index=False, border=0, classes="tabela-dados")
    
    descricao_anexos = (
        "A planilha diária (.xlsx), o histórico (.csv) e os relatórios semanais foram anexados."
        if caminho_csv else "A planilha diária (.xlsx) foi anexada."
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
            .badge-sexta {{ display: inline-block; padding: 4px 8px; border-radius: 6px; background-color: #dcfce7; color: #15803d; font-weight: 600; font-size: 12px; margin-left: 6px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>📱 Monitoramento de Preços - Paraguai</h2>
            <p>Relatório gerado automaticamente em <strong>{datetime.now().strftime('%d/%m/%Y às %H:%M')}</strong>.</p>
            <span class="badge">Total de Modelos: {len(df)}</span>
            {"<span class='badge-sexta'>⭐ Infográfico Semanal Anexado</span>" if eh_sexta or anexos_extras else ""}
            
            {tabela_html}
            
            <p class="footer">
                Fonte: Compras Paraguai (Ciudad del Este)<br>
                {descricao_anexos}
            </p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))
    
    # Anexar arquivos
    lista_anexos = []
    if caminho_xlsx and os.path.exists(caminho_xlsx):
        lista_anexos.append(caminho_xlsx)
    if caminho_csv and os.path.exists(caminho_csv):
        lista_anexos.append(caminho_csv)
    if anexos_extras:
        for a in anexos_extras:
            if a and os.path.exists(a):
                lista_anexos.append(a)

    for arquivo in lista_anexos:
        try:
            with open(arquivo, "rb") as anexo:
                tipo_mime = mimetypes.guess_type(arquivo)[0] or "application/octet-stream"
                tipo_principal, subtipo = tipo_mime.split("/", 1)
                part = MIMEBase(tipo_principal, subtipo)
                part.set_payload(anexo.read())
            encoders.encode_base64(part)
            nome_arquivo = os.path.basename(arquivo)
            part.add_header("Content-Disposition", f"attachment; filename={nome_arquivo}")
            msg.attach(part)
            print(f"[+] Anexo adicionado: {nome_arquivo}")
        except Exception as e:
            print(f"[!] Erro ao anexar {arquivo}: {e}")

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

def enviar_email_erro(detalhes):
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        print("[!] Alerta por e-mail não enviado: remetente ou senha SMTP não configurados.")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    msg["Subject"] = f"[ERRO] Pesquisa iPhone Paraguai - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    msg.attach(MIMEText(
        f"A rotina de pesquisa de preços falhou em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}.\n\n"
        f"Detalhes do erro:\n{detalhes}\n\nO trecho recente de execucao_log.txt está anexado quando disponível.",
        "plain",
        "utf-8",
    ))

    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except (AttributeError, OSError, ValueError):
        pass

    caminho_log = os.path.join(os.path.dirname(__file__), "execucao_log.txt")
    try:
        with open(caminho_log, "rb") as arquivo_log:
            log_recente = arquivo_log.read()[-50000:].decode("utf-8", errors="replace")
        if log_recente:
            anexo_log = MIMEText(log_recente, "plain", "utf-8")
            anexo_log.add_header("Content-Disposition", "attachment", filename="execucao_log.txt")
            msg.attach(anexo_log)
    except OSError as e:
        print(f"[!] Não foi possível anexar execucao_log.txt: {e}")

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20) as servidor:
                servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
                servidor.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as servidor:
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
                servidor.send_message(msg)
        print(f"[+] Alerta de erro enviado para {EMAIL_DESTINO}.")
        return True
    except Exception as e:
        print(f"[X] Não foi possível enviar o alerta de erro: {e}")
        return False

def enviar_email_teste():
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        print("[X] Teste não enviado: EMAIL_REMETENTE ou EMAIL_SENHA não configurados.")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    msg["Subject"] = f"[TESTE] Monitoramento iPhone Paraguai - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    msg.attach(MIMEText(
        "Teste de envio executado pelo GitHub Actions.\n"
        "Esta mensagem confirma a conexão SMTP e não representa um relatório de preços.",
        "plain",
        "utf-8",
    ))

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20) as servidor:
                servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
                servidor.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as servidor:
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
                servidor.send_message(msg)
        print(f"[+] E-mail de teste enviado para {EMAIL_DESTINO}.")
        return True
    except Exception as e:
        print(f"[X] Falha no teste SMTP: {type(e).__name__}: {e}")
        return False

def _reportar_excecao(tipo, valor, tb):
    detalhes = "".join(traceback.format_exception(tipo, valor, tb))
    enviar_email_erro(detalhes)
    sys.__excepthook__(tipo, valor, tb)

sys.excepthook = _reportar_excecao

def obter_caminho_desktop():
    caminho_configurado = os.getenv("IPHONE_OUTPUT_DIR", "").strip()
    if caminho_configurado:
        caminho = os.path.abspath(caminho_configurado)
        os.makedirs(caminho, exist_ok=True)
        return caminho

    desktop = os.path.expanduser(r"~\OneDrive\Área de Trabalho")
    if not os.path.exists(desktop):
        desktop = os.path.expanduser(r"~\Desktop")
    if not os.path.exists(desktop):
        desktop = os.getcwd()
    return desktop

def salvar_historico_cumulativo(df_novo, caminho_csv):
    """Garante que o histórico não seja sobrescrito, acumulando os dias de coleta."""
    if os.path.exists(caminho_csv):
        try:
            df_existente = pd.read_csv(caminho_csv)
            df_combinado = pd.concat([df_existente, df_novo], ignore_index=True)
            # Remove duplicatas exatas se houver
            df_combinado.drop_duplicates(subset=["Data", "Modelo", "Loja", "Variante", "Preco_BRL"], inplace=True)
            df_combinado.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
            print(f"[+] Histórico consolidado salvo ({len(df_combinado)} registros no total): {caminho_csv}")
            return df_combinado
        except Exception as e:
            print(f"[!] Erro ao mesclar com histórico existente: {e}. Salvando novo arquivo.")
    
    df_novo.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
    print(f"[+] Novo arquivo de histórico salvo: {caminho_csv}")
    return df_novo

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Monitor de Preços iPhone no Paraguai")
    parser.add_argument("--forcar-sexta", action="store_true", help="Força a geração do infográfico independente do dia")
    parser.add_argument("--teste-email", action="store_true", help="Envia um e-mail de teste sem executar a pesquisa")
    parser.add_argument("--termo", default="iphone 17 pro max", help="Termo para pesquisa de preços")
    args = parser.parse_args()

    if args.teste_email:
        sys.exit(0 if enviar_email_teste() else 1)

    # Verifica se hoje é sexta-feira (4 = Friday) ou se a flag foi passada
    eh_sexta_feira = (datetime.now().weekday() == 4) or args.forcar_sexta

    print("=" * 60)
    print(f"🚀 INICIANDO MONITORAMENTO DE PREÇOS NO PARAGUAI")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (Sexta-feira: {eh_sexta_feira})")
    print("=" * 60)

    dados = raspar_precos_paraguai(args.termo)
    
    if dados:
        df_hoje = pd.DataFrame(dados)
        cotacao_dolar = obter_cotacao_dolar()
        df_hoje["Cotacao_USD_BRL"] = cotacao_dolar["valor"] if cotacao_dolar else None
        df_hoje["Data_Cotacao_USD"] = cotacao_dolar["data"] if cotacao_dolar else None
        if not cotacao_dolar:
            enviar_email_erro("A pesquisa foi coletada, mas a cotação PTAX do dólar não foi obtida. O XLSX indicará a indisponibilidade.")
        print(f"\n[+] SUCESSO! Encontrados {len(df_hoje)} modelos na coleta de hoje.\n")
        
        # 1. Salva o histórico acumulado no mesmo local (Desktop e cópia local)
        desktop = obter_caminho_desktop()
        caminho_csv_desktop = os.path.join(desktop, "historico_iphone_paraguai.csv")
        df_historico = salvar_historico_cumulativo(df_hoje, caminho_csv_desktop)
        caminho_xlsx_diario = os.path.join(
            desktop,
            f"relatorio_iphone_paraguai_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        )
        salvar_relatorio_excel(df_hoje, caminho_xlsx_diario, cotacao_dolar)

        # Cópia local no repositório
        caminho_csv_local = os.path.join(os.path.dirname(__file__), "historico_iphone_paraguai.csv")
        try:
            df_historico.to_csv(caminho_csv_local, index=False, encoding="utf-8-sig")
        except Exception:
            pass

        # 2. Se for Sexta-feira, executa o Infográfico Semanal
        anexos_extras = []
        falha_infografico = False
        if eh_sexta_feira:
            print("\n" + "#" * 60)
            print("📈 HOJE É SEXTA-FEIRA: GERANDO INFOGRÁFICO EXECUTIVO DE PREÇOS")
            print("#" * 60)
            
            try:
                # Importa o gerador do infográfico
                sys.path.append(os.path.dirname(__file__))
                from gerador_infografico import gerar_infografico_html
                
                # Salva infográfico no Desktop (mesmo local da rotina)
                data_tag = datetime.now().strftime("%Y-%m-%d")
                caminho_html_desktop = os.path.join(desktop, "infografico_precos_paraguai.html")
                caminho_html_historico = os.path.join(desktop, f"infografico_precos_paraguai_{data_tag}.html")
                caminho_html_local = os.path.join(os.path.dirname(__file__), "infografico_precos_paraguai.html")

                # Gera o arquivo HTML
                gerar_infografico_html(caminho_csv_desktop, caminho_html_desktop)
                gerar_infografico_html(caminho_csv_desktop, caminho_html_historico)
                gerar_infografico_html(caminho_csv_desktop, caminho_html_local)

                anexos_extras.append(caminho_html_desktop)
                print(f"[+] Infográfico Semanal disponível em:\n    -> {caminho_html_desktop}\n    -> {caminho_html_historico}")
            except Exception as e:
                print(f"[X] Erro ao gerar infográfico: {e}")
                falha_infografico = True
                enviar_email_erro(f"Falha ao gerar o infográfico semanal: {e}\n\n{traceback.format_exc()}")

        # 3. Dispara o envio por e-mail com os anexos (CSV + Infográfico se sexta)
        if not enviar_relatorio_email(
            df_hoje,
            caminho_csv_desktop if eh_sexta_feira else None,
            anexos_extras,
            caminho_xlsx_diario,
        ):
            enviar_email_erro("A coleta foi concluída, mas o relatório diário não pôde ser enviado. Consulte execucao_log.txt para ver a causa registrada.")
            sys.exit(1)
        if falha_infografico:
            print("[X] Relatório enviado, mas a geração do infográfico falhou.")
            sys.exit(1)
        print("\n[✔] Rotina concluída com sucesso!")
    else:
        print("[!] Nenhum resultado foi extraído.")
        enviar_email_erro("A coleta terminou sem encontrar resultados. Verifique a disponibilidade do site e o log execucao_log.txt.")
        sys.exit(1)

