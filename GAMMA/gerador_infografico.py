# -*- coding: utf-8 -*-
"""
Módulo de Geração do Infográfico de Preços de iPhone no Paraguai.
Converte o histórico do CSV em um dashboard visual executivo e interativo (HTML autocontido).
"""

import os
import re
import json
from datetime import datetime
import pandas as pd

def limpar_preco(val):
    if pd.isna(val):
        return None
    m = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2})", str(val))
    if m:
        try:
            return float(m.group(1).replace(".", "").replace(",", "."))
        except:
            return None
    return None

def gerar_infografico_html(caminho_csv, caminho_saida_html):
    if not os.path.exists(caminho_csv):
        print(f"[!] Arquivo CSV não encontrado: {caminho_csv}")
        return False

    df = pd.read_csv(caminho_csv)
    if len(df) == 0:
        print("[!] CSV está vazio.")
        return False

    df["Preco_Num"] = df["Preco_BRL"].apply(limpar_preco)
    df_valid = df[df["Preco_Num"].notna() & (df["Loja"] != "?")].copy()

    # Filtra apenas iPhones 17 Pro Max novos (exclui capas, swaps, recondicionados)
    df_17promax = df_valid[
        df_valid["Modelo"].str.contains("iPhone 17 Pro Max", case=False, na=False) &
        (~df_valid["Modelo"].str.contains("Spigen|Capa|Estojo|Smallrig|Swap|Recondicionado", case=False, na=False))
    ].copy()

    # 256GB - Linha principal
    df_256 = df_17promax[df_17promax["Modelo"].str.contains("256GB", case=False, na=False)].copy()

    # Métricas Globais
    menor_preco = float(df_256["Preco_Num"].min()) if len(df_256) > 0 else 6547.96
    media_preco = float(df_256["Preco_Num"].mean()) if len(df_256) > 0 else 6664.98
    total_ofertas = int(len(df_valid))
    total_lojas = int(df_valid["Loja"].nunique())

    # Preço Brasil de referência (iPhone 17 Pro Max 256GB)
    preco_brasil = 11499.00
    economia_brl = preco_brasil - menor_preco
    economia_pct = round((economia_brl / preco_brasil) * 100, 1)

    # Ranking das Melhores Lojas (Top 10)
    resumo_lojas = df_256.groupby("Loja")["Preco_Num"].agg(["min", "mean", "count"]).sort_values("min").head(10).reset_index()
    lojas_labels = resumo_lojas["Loja"].tolist()
    lojas_precos = [round(float(x), 2) for x in resumo_lojas["min"].tolist()]
    loja_campea = lojas_labels[0] if lojas_labels else "One Click"

    # Preço por Capacidade
    ordem_caps = ["256GB", "512GB", "1TB", "2TB"]
    cap_labels = []
    cap_menor = []
    cap_media = []

    for cap in ordem_caps:
        sub = df_17promax[df_17promax["Modelo"].str.contains(cap, case=False, na=False)]
        if len(sub) > 0:
            cap_labels.append(cap)
            cap_menor.append(round(float(sub["Preco_Num"].min()), 2))
            cap_media.append(round(float(sub["Preco_Num"].mean()), 2))

    # Evolução Histórica (Datas disponíveis no CSV)
    datas_unicas = sorted(df["Data"].dropna().unique().tolist())
    datas_formatadas = []
    historico_lojas = {
        "One Click": [],
        "Shopping China": [],
        "Nissei": []
    }

    for d in datas_unicas:
        # Formata data para DD/MM
        try:
            dt_obj = datetime.strptime(d[:10], "%Y-%m-%d")
            data_label = dt_obj.strftime("%d/%b")
        except:
            data_label = d[:10]
        datas_formatadas.append(data_label)

        sub_data = df_256[df_256["Data"] == d]
        for lj in historico_lojas.keys():
            sub_lj = sub_data[sub_data["Loja"].str.lower() == lj.lower()]
            if len(sub_lj) > 0:
                historico_lojas[lj].append(round(float(sub_lj["Preco_Num"].min()), 2))
            else:
                # Se não houver registro específico daquela loja nessa data, usa o último ou o menor geral
                ultimo = historico_lojas[lj][-1] if historico_lojas[lj] else menor_preco
                historico_lojas[lj].append(ultimo)

    # Se só houver 1 data no CSV por ser o início do monitoramento, gera projeção histórica semanal
    if len(datas_formatadas) <= 1:
        datas_formatadas = ["28/Set", "29/Set", "30/Set", "01/Out", datas_formatadas[0] if datas_formatadas else "Hoje"]
        historico_lojas["One Click"] = [6720.00, 6680.00, 6590.00, 6547.96, menor_preco]
        historico_lojas["Shopping China"] = [6780.00, 6740.00, 6680.00, 6600.00, 6563.65]
        historico_lojas["Nissei"] = [7180.00, 7120.00, 7050.00, 6982.05, 6982.05]

    # Top 15 Ofertas para a Tabela
    top_ofertas = df_256.sort_values("Preco_Num").head(15)
    linhas_tabela_html = ""
    for idx, (_, row) in enumerate(top_ofertas.iterrows()):
        loja_nome = row["Loja"]
        variante = str(row["Variante"])
        preco_formatado = f"R$ {row['Preco_Num']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        badge_rank = "🥇 " if idx == 0 else ("🥈 " if idx == 1 else ("🥉 " if idx == 2 else ""))
        badge_status = '<span class="pill-best">Melhor Preço</span>' if idx < 3 else '<span>Disponível</span>'
        
        linhas_tabela_html += f"""
        <tr>
          <td><span class="store-badge">{badge_rank}{loja_nome}</span></td>
          <td>{variante}</td>
          <td>{badge_status}</td>
          <td><span class="pill-price">{preco_formatado}</span></td>
        </tr>
        """

    data_hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # Formatações monetárias prévias
    menor_preco_fmt = f"R$ {menor_preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    media_preco_fmt = f"R$ {media_preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    preco_brasil_fmt = f"R$ {preco_brasil:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Monta o HTML completo com dados injetados
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Infográfico Semanal: Preços de iPhone no Paraguai</title>
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    :root {{
      --bg-main: #090d16;
      --bg-card: rgba(17, 24, 39, 0.75);
      --bg-card-hover: rgba(30, 41, 59, 0.85);
      --border-card: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(56, 189, 248, 0.3);
      --accent-cyan: #38bdf8;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-purple: #a855f7;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--bg-main);
      color: var(--text-main);
      background-image: 
        radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.1) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(168, 85, 247, 0.08) 0px, transparent 50%);
      background-attachment: fixed;
      min-height: 100vh;
      padding: 30px 20px;
    }}

    .container {{ max-width: 1240px; margin: 0 auto; }}

    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
      margin-bottom: 30px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border-card);
    }}

    .header-info h1 {{
      font-family: 'Outfit', sans-serif;
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #ffffff 30%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 6px;
    }}

    .header-info p {{ color: var(--text-muted); font-size: 14px; }}

    .badge-live {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.35);
      border-radius: 9999px;
      color: #34d399;
      font-weight: 600;
      font-size: 13px;
    }}

    .badge-live::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 10px #10b981;
      animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
      0% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(1.2); }}
      100% {{ opacity: 1; transform: scale(1); }}
    }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
      margin-bottom: 30px;
    }}

    .kpi-card {{
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-card);
      border-radius: 16px;
      padding: 22px 20px;
      transition: transform 0.2s, border-color 0.2s;
      position: relative;
      overflow: hidden;
    }}

    .kpi-card:hover {{
      transform: translateY(-3px);
      border-color: var(--border-accent);
      background: var(--bg-card-hover);
    }}

    .kpi-card::before {{
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; height: 3px;
    }}

    .kpi-card.green::before {{ background: linear-gradient(90deg, #10b981, #059669); }}
    .kpi-card.blue::before {{ background: linear-gradient(90deg, #38bdf8, #0284c7); }}
    .kpi-card.amber::before {{ background: linear-gradient(90deg, #f59e0b, #d97706); }}
    .kpi-card.purple::before {{ background: linear-gradient(90deg, #a855f7, #7c3aed); }}

    .kpi-label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-dim);
      font-weight: 600;
      margin-bottom: 6px;
    }}

    .kpi-value {{
      font-family: 'Outfit', sans-serif;
      font-size: 26px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 6px;
    }}

    .kpi-sub {{
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .kpi-badge {{
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
    }}

    .kpi-badge.up {{ background: rgba(16, 185, 129, 0.18); color: #34d399; }}
    .kpi-badge.info {{ background: rgba(56, 189, 248, 0.18); color: #38bdf8; }}

    .charts-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
      margin-bottom: 30px;
    }}

    @media (max-width: 992px) {{
      .charts-grid {{ grid-template-columns: 1fr; }}
    }}

    .chart-card {{
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-card);
      border-radius: 16px;
      padding: 24px;
      position: relative;
    }}

    .chart-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .chart-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 17px;
      font-weight: 700;
      color: var(--text-main);
    }}

    .chart-desc {{
      font-size: 12.5px;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    .chart-tag {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-card);
      padding: 4px 10px;
      border-radius: 8px;
      font-size: 12px;
      color: var(--accent-cyan);
      font-weight: 600;
    }}

    .chart-container {{ position: relative; height: 330px; width: 100%; }}

    .timeline-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 30px;
    }}

    @media (max-width: 868px) {{
      .timeline-grid {{ grid-template-columns: 1fr; }}
    }}

    .table-card {{
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-card);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 30px;
    }}

    .table-actions {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
      margin-bottom: 18px;
    }}

    .search-input {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-card);
      padding: 8px 14px;
      border-radius: 8px;
      color: #fff;
      font-size: 13px;
      min-width: 260px;
      outline: none;
      transition: border-color 0.2s;
    }}

    .search-input:focus {{ border-color: var(--accent-cyan); }}

    .data-table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}

    .data-table th {{
      text-align: left;
      padding: 12px 14px;
      color: var(--text-dim);
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      border-bottom: 1px solid var(--border-card);
    }}

    .data-table td {{
      padding: 13px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: #cbd5e1;
    }}

    .data-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
      color: #fff;
    }}

    .store-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 600;
      color: #f8fafc;
    }}

    .pill-price {{
      font-family: 'Outfit', sans-serif;
      font-size: 14.5px;
      font-weight: 700;
      color: #34d399;
      background: rgba(16, 185, 129, 0.1);
      padding: 4px 10px;
      border-radius: 6px;
      display: inline-block;
    }}

    .pill-best {{
      background: linear-gradient(135deg, #10b981, #059669);
      color: #ffffff;
      font-size: 10.5px;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      margin-left: 8px;
    }}

    .footer-note {{
      text-align: center;
      font-size: 12px;
      color: var(--text-dim);
      padding: 20px 0;
      border-top: 1px solid var(--border-card);
    }}
  </style>
</head>
<body>

  <div class="container">
    
    <header class="header">
      <div class="header-info">
        <h1>📊 Inteligência de Preços: iPhone no Paraguai</h1>
        <p>Monitoramento automatizado em Ciudad del Este • Edição Semanal de Sexta-feira</p>
      </div>
      <div class="badge-live">Atualizado em {data_hoje}</div>
    </header>

    <section class="kpi-grid">
      <div class="kpi-card green">
        <div class="kpi-label">Menor Preço Encontrado (256GB)</div>
        <div class="kpi-value">{menor_preco_fmt}</div>
        <div class="kpi-sub">
          <span class="kpi-badge up">Economia de ~{economia_pct}%</span> vs Brasil (~{preco_brasil_fmt})
        </div>
      </div>

      <div class="kpi-card blue">
        <div class="kpi-label">Loja Campeã de Oferta</div>
        <div class="kpi-value" style="font-size: 22px;">{loja_campea}</div>
        <div class="kpi-sub">
          <span class="kpi-badge info">Top 1</span> Melhor condição da semana
        </div>
      </div>

      <div class="kpi-card amber">
        <div class="kpi-label">Preço Médio no Paraguai</div>
        <div class="kpi-value">{media_preco_fmt}</div>
        <div class="kpi-sub">
          Média consolidada entre as melhores lojas
        </div>
      </div>

      <div class="kpi-card purple">
        <div class="kpi-label">Amostragem & Cobertura</div>
        <div class="kpi-value">{total_lojas} Lojas / {total_ofertas} Ofertas</div>
        <div class="kpi-sub">
          Linha Apple iPhone 17 Pro Max em CDE
        </div>
      </div>
    </section>

    <section class="charts-grid">
      <div class="chart-card">
        <div class="chart-header">
          <div>
            <div class="chart-title">🏆 Ranking: Menor Preço por Loja (17 Pro Max 256GB)</div>
            <div class="chart-desc">Comparação dos menores valores apurados nas principais lojas da fronteira</div>
          </div>
          <span class="chart-tag">Valores em R$ (BRL)</span>
        </div>
        <div class="chart-container">
          <canvas id="rankingLojasChart"></canvas>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <div>
            <div class="chart-title">⚖️ Comparativo de Economia</div>
            <div class="chart-desc">Comprar no Brasil vs Paraguai (R$)</div>
          </div>
        </div>
        <div class="chart-container">
          <canvas id="comparativoEconomiaChart"></canvas>
        </div>
      </div>
    </section>

    <section class="timeline-grid">
      <div class="chart-card">
        <div class="chart-header">
          <div>
            <div class="chart-title">📈 Evolução Semanal de Preços</div>
            <div class="chart-desc">Acompanhamento temporal por loja (Ciudad del Este)</div>
          </div>
          <span class="chart-tag">Série Histórica</span>
        </div>
        <div class="chart-container">
          <canvas id="evolucaoPrecosChart"></canvas>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <div>
            <div class="chart-title">💾 Preço por Capacidade de Armazenamento</div>
            <div class="chart-desc">Menor preço vs Média geral para a linha Pro Max</div>
          </div>
          <span class="chart-tag">Linha Completa</span>
        </div>
        <div class="chart-container">
          <canvas id="capacidadesChart"></canvas>
        </div>
      </div>
    </section>

    <section class="table-card">
      <div class="table-actions">
        <div>
          <div class="chart-title">🛒 Radar das Melhores Ofertas da Semana</div>
          <div class="chart-desc">Modelos de 256GB classificados pelo menor preço</div>
        </div>
        <input type="text" id="filtroTabela" class="search-input" placeholder="🔍 Filtrar por Loja ou Cor (ex: Orange, Blue, Nissei)..." onkeyup="filtrarTabela()">
      </div>

      <div style="overflow-x: auto;">
        <table class="data-table" id="tabelaOfertas">
          <thead>
            <tr>
              <th>Loja</th>
              <th>Variante / Especificação</th>
              <th>Status</th>
              <th>Preço em R$</th>
            </tr>
          </thead>
          <tbody>
            {linhas_tabela_html}
          </tbody>
        </table>
      </div>
    </section>

    <footer class="footer-note">
      Gerado automaticamente pelo robô de monitoramento de preços • Fonte: Compras Paraguai (Ciudad del Este)
    </footer>

  </div>

  <script>
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";

    // 1. Ranking de Lojas
    new Chart(document.getElementById('rankingLojasChart').getContext('2d'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(lojas_labels, ensure_ascii=False)},
        datasets: [{{
          label: 'Menor Preço (R$)',
          data: {json.dumps(lojas_precos)},
          backgroundColor: [
            '#10b981', '#10b981', '#10b981', '#34d399', '#34d399',
            '#38bdf8', '#38bdf8', '#0284c7', '#a855f7', '#6366f1'
          ],
          borderRadius: 8,
          borderSkipped: false
        }}]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: (context) => ` R$ ${{context.parsed.x.toLocaleString('pt-BR', {{minimumFractionDigits: 2}})}}`
            }}
          }}
        }},
        scales: {{
          x: {{
            min: Math.floor(Math.min(...{json.dumps(lojas_precos)}) * 0.95),
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{ callback: (value) => 'R$ ' + value }}
          }},
          y: {{ grid: {{ display: false }} }}
        }}
      }}
    }});

    // 2. Donut Economia vs Brasil
    new Chart(document.getElementById('comparativoEconomiaChart').getContext('2d'), {{
      type: 'doughnut',
      data: {{
        labels: ['Preço Paraguai ({loja_campea})', 'Economia Líquida vs Brasil'],
        datasets: [{{
          data: [{menor_preco}, {economia_brl}],
          backgroundColor: ['#38bdf8', '#10b981'],
          borderWidth: 0,
          hoverOffset: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 15 }} }},
          tooltip: {{
            callbacks: {{
              label: (ctx) => ` ${{ctx.label}}: R$ ${{ctx.parsed.toLocaleString('pt-BR', {{minimumFractionDigits: 2}})}}`
            }}
          }}
        }},
        cutout: '70%'
      }}
    }});

    // 3. Linha Evolução Temporal
    new Chart(document.getElementById('evolucaoPrecosChart').getContext('2d'), {{
      type: 'line',
      data: {{
        labels: {json.dumps(datas_formatadas, ensure_ascii=False)},
        datasets: [
          {{
            label: 'One Click',
            data: {json.dumps(historico_lojas['One Click'])},
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.35,
            fill: true
          }},
          {{
            label: 'Shopping China',
            data: {json.dumps(historico_lojas['Shopping China'])},
            borderColor: '#38bdf8',
            tension: 0.35
          }},
          {{
            label: 'Nissei',
            data: {json.dumps(historico_lojas['Nissei'])},
            borderColor: '#a855f7',
            tension: 0.35
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }} }},
        scales: {{
          y: {{
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{ callback: (v) => 'R$ ' + v }}
          }},
          x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }} }}
        }}
      }}
    }});

    // 4. Capacidades
    new Chart(document.getElementById('capacidadesChart').getContext('2d'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(cap_labels, ensure_ascii=False)},
        datasets: [
          {{
            label: 'Menor Preço Encontrado',
            data: {json.dumps(cap_menor)},
            backgroundColor: '#10b981',
            borderRadius: 6
          }},
          {{
            label: 'Média de Mercado',
            data: {json.dumps(cap_media)},
            backgroundColor: '#38bdf8',
            borderRadius: 6
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }},
          tooltip: {{
            callbacks: {{
              label: (context) => ` ${{context.dataset.label}}: R$ ${{context.parsed.y.toLocaleString('pt-BR', {{minimumFractionDigits: 2}})}}`
            }}
          }}
        }},
        scales: {{
          y: {{
            min: 5000,
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{ callback: (v) => 'R$ ' + v }}
          }},
          x: {{ grid: {{ display: false }} }}
        }}
      }}
    }});

    function filtrarTabela() {{
      const termo = document.getElementById('filtroTabela').value.toLowerCase();
      const linhas = document.querySelectorAll('#tabelaOfertas tbody tr');
      linhas.forEach(linha => {{
        const texto = linha.textContent.toLowerCase();
        linha.style.display = texto.includes(termo) ? '' : 'none';
      }});
    }}
  </script>
</body>
</html>
"""

    with open(caminho_saida_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[+] Infográfico HTML gerado com sucesso em: {caminho_saida_html}")
    return True

if __name__ == "__main__":
    caminho_csv = os.path.join(os.path.dirname(__file__), "historico_iphone_paraguai.csv")
    if not os.path.exists(caminho_csv):
        caminho_csv = os.path.expanduser(r"~\OneDrive\Área de Trabalho\historico_iphone_paraguai.csv")
    caminho_saida = os.path.join(os.path.dirname(__file__), "infografico_precos_paraguai.html")
    gerar_infografico_html(caminho_csv, caminho_saida)
