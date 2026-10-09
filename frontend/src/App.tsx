import React, { useState } from 'react';
import axios from 'axios';
import { 
  BarElement, 
  CategoryScale, 
  Chart as ChartJS, 
  Legend, 
  LinearScale, 
  Title, 
  Tooltip, 
  PointElement, 
  LineElement, 
  ArcElement 
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import { 
  Upload, 
  FileDown, 
  FileText, 
  LayoutDashboard, 
  Eye, 
  Sparkles, 
  AlertTriangle, 
  RefreshCw,
  Volume2
} from 'lucide-react';
import AudioPlayer from './components/AudioPlayer';
import ParallaxBackground from './components/ParallaxBackground';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const API_BASE = 'http://localhost:8000';

// Mock data for immediate preview
const MOCK_DATA = {
  summary: {
    total_value: 125450.80,
    avg_transaction: 2509.02,
    count_suppliers: 12,
    count_transactions: 50
  },
  suppliers: {
    "Tech Solutions": 35000,
    "Global Logistics": 28000,
    "Office Supply Co": 15000,
    "Alpha Services": 12000,
    "Beta Industries": 9500,
    "Delta Corp": 8000,
    "Sigma Systems": 7500,
    "Zeta Works": 5450,
    "Gamma Group": 3000,
    "Omega Ltd": 2000
  },
  trends: {
    "2026-01-31": 15000,
    "2026-02-28": 22000,
    "2026-03-31": 18500,
    "2026-04-30": 28000,
    "2026-05-31": 31000,
    "2026-06-30": 10950
  }
};

const MOCK_INSIGHTS = `### Tendências Principais
- **Concentração de Gastos**: Os top 3 fornecedores (Tech Solutions, Global Logistics e Office Supply Co) respondem por mais de **60% do total transacionado**, sinalizando dependência estratégica.
- **Evolução Temporal**: Houve um pico expressivo de faturamento em maio (R$ 31.000,00) seguido por um recuo considerável em junho. Recomenda-se analisar se houve sazonalidade ou antecipação de compras.

### Recomendações Práticas
1. **Negociação de Volume**: Iniciar renegociação de prazos ou descontos com a *Tech Solutions*, dado o volume expressivo de compras concentradas.
2. **Diversificação**: Avaliar novos fornecedores para as categorias de menor porte a fim de mitigar riscos operacionais.`;

function App() {
  const [data, setData] = useState<any>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insights, setInsights] = useState<string | null>(null);
  const [playingSection, setPlayingSection] = useState<{ title: string; text: string } | null>(null);

  const fetchInsights = async () => {
    setInsightsLoading(true);
    setInsights(null);
    try {
      const response = await axios.get(`${API_BASE}/insights`);
      setInsights(response.data.insights);
    } catch (error: any) {
      console.error("Failed to fetch insights", error);
      setInsights("Erro: Não foi possível obter os insights. Verifique a conexão com o servidor.");
    } finally {
      setInsightsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadLoading(true);
    setData(null);
    setInsights(null);
    setPlayingSection(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/upload`, formData);
      setData(response.data);
      // Trigger insights fetch asynchronously after upload success
      setUploadLoading(false);
      fetchInsights();
    } catch (error) {
      console.error("Upload failed", error);
      alert("Erro ao conectar com o backend. Certifique-se que o servidor Python está rodando.");
      setUploadLoading(false);
    }
  };

  const loadDemo = () => {
    setUploadLoading(true);
    setData(null);
    setInsights(null);
    setPlayingSection(null);
    setTimeout(() => {
      setData(MOCK_DATA);
      setUploadLoading(false);
      setInsightsLoading(true);
      setTimeout(() => {
        setInsights(MOCK_INSIGHTS);
        setInsightsLoading(false);
      }, 1000);
    }, 800);
  };

  const downloadReport = async (type: string) => {
    if (data === MOCK_DATA) {
      alert("Esta é uma demonstração visual. Para baixar relatórios reais, carregue um arquivo Excel.");
      return;
    }
    try {
      const response = await axios.get(`${API_BASE}/reports/${type}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Relatorio_Analytics_${type}.${type}`);
      document.body.appendChild(link);
      link.click();
    } catch (error) {
      console.error("Report download failed", error);
    }
  };

  const openFilterReport = (op = 2700, subOp = 2707) => {
    const url = `${API_BASE}/filter_report?op=${op}&sub_op=${subOp}&format=html`;
    window.open(url, '_blank');
  };

  const openPlotlyReport = () => {
    const url = `${API_BASE}/plotly_report`;
    window.open(url, '_blank');
  };

  const helperRenderBoldText = (text: string) => {
    const parts = text.split('**');
    return parts.map((part, i) => i % 2 === 1 ? <strong key={i}>{part}</strong> : part);
  };

  const parseMarkdown = (markdownText: string | null) => {
    if (!markdownText) return null;
    
    // Check if the output is an API Key error message
    if (markdownText.includes("GOOGLE_API_KEY") || markdownText.includes("Chave de API do Google não configurada")) {
      return (
        <div className="warning-alert">
          <h4>
            <AlertTriangle size={18} /> Chave de API Não Configurada
          </h4>
          <p>
            O serviço de insights inteligentes utiliza o modelo **Gemini**. Para ativá-lo, crie um arquivo com o nome <code>.env</code> na raiz da pasta do backend com as seguintes credenciais:
          </p>
          <pre style={{ background: '#fef3c7', padding: '0.5rem', borderRadius: '0.25rem', overflowX: 'auto', fontSize: '0.8rem', margin: '0.25rem 0' }}>
            GOOGLE_API_KEY=AIzaSy...seu_token_aqui
          </pre>
          <p style={{ margin: 0 }}>
            Após criar o arquivo, clique em <strong>Recarregar Insights</strong> para processar os dados novamente.
          </p>
        </div>
      );
    }

    const lines = markdownText.split('\n');
    interface SectionBlock {
      title: string | null;
      lines: string[];
    }
    const blocks: SectionBlock[] = [];
    let currentBlock: SectionBlock = { title: null, lines: [] };

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('###') || trimmed.startsWith('##')) {
        if (currentBlock.title !== null || currentBlock.lines.length > 0) {
          blocks.push(currentBlock);
        }
        currentBlock = {
          title: trimmed.replace(/^#+\s*/, ''),
          lines: []
        };
      } else {
        currentBlock.lines.push(line);
      }
    }
    if (currentBlock.title !== null || currentBlock.lines.length > 0) {
      blocks.push(currentBlock);
    }

    return blocks.map((block, blockIdx) => {
      const isCurrentActive = playingSection && playingSection.title === block.title;
      const sectionText = block.lines.join('\n').trim();

      return (
        <div 
          key={blockIdx} 
          className={`section-block ${isCurrentActive ? 'section-block-active' : ''}`}
          style={{ marginBottom: '1.25rem' }}
        >
          {block.title && (
            <div className="section-header-row">
              <h4>{helperRenderBoldText(block.title)}</h4>
              <button
                type="button"
                className={`btn-section-audio ${isCurrentActive ? 'active' : ''}`}
                onClick={() => {
                  if (isCurrentActive) {
                    setPlayingSection(null);
                  } else {
                    setPlayingSection({
                      title: block.title!,
                      text: `${block.title}. ${sectionText}`
                    });
                  }
                }}
                title={isCurrentActive ? "Parar de focar nesta seção" : `Ouvir ${block.title}`}
              >
                <Volume2 size={13} />
                <span>{isCurrentActive ? 'Ouvindo...' : 'Ouvir Seção'}</span>
              </button>
            </div>
          )}
          
          <div className="section-lines">
            {block.lines.map((line, idx) => {
              const trimmed = line.trim();
              if (!trimmed) return <div key={idx} style={{ height: '0.25rem' }} />;
              
              if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
                const bulletText = trimmed.replace(/^[\-\*]\s*/, '');
                return (
                  <ul key={idx} style={{ listStyleType: 'disc', margin: '0.25rem 0 0.25rem 1.25rem' }}>
                    <li>{helperRenderBoldText(bulletText)}</li>
                  </ul>
                );
              }

              if (/^\d+\./.test(trimmed)) {
                const bulletText = trimmed.replace(/^\d+\.\s*/, '');
                return (
                  <ol key={idx} style={{ margin: '0.25rem 0 0.25rem 1.25rem' }}>
                    <li>{helperRenderBoldText(bulletText)}</li>
                  </ol>
                );
              }

              return <p key={idx} style={{ margin: '0 0 0.5rem 0' }}>{helperRenderBoldText(trimmed)}</p>;
            })}
          </div>
        </div>
      );
    });
  };

  const supplierData = data ? {
    labels: Object.keys(data.suppliers),
    datasets: [{
      label: 'Valor por Fornecedor (R$)',
      data: Object.values(data.suppliers),
      backgroundColor: 'rgba(79, 70, 229, 0.85)',
      hoverBackgroundColor: 'rgba(67, 56, 202, 1)',
      borderRadius: 6,
    }]
  } : null;

  const trendData = data ? {
    labels: Object.keys(data.trends).map(d => {
      const date = new Date(d);
      return isNaN(date.getTime()) ? d : date.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
    }),
    datasets: [{
      label: 'Volume de Compras no Tempo',
      data: Object.values(data.trends),
      borderColor: '#10b981',
      tension: 0.35,
      fill: true,
      backgroundColor: 'rgba(16, 185, 129, 0.08)',
      pointBackgroundColor: '#10b981',
      pointBorderColor: '#fff',
      pointHoverRadius: 6,
    }]
  } : null;

  const isConfigError = insights && (insights.includes("GOOGLE_API_KEY") || insights.includes("Chave de API"));

  return (
    <>
      <ParallaxBackground />
      <div className="app-container">
      <header className="header">
        <div className="logo-section">
          <h1>Analytics Pro</h1>
          <p>Dashboard Inteligente para Decisões Estratégicas</p>
        </div>
        {data && !uploadLoading && (
          <div className="reports-section">
            <button onClick={() => downloadReport('pptx')} className="btn-report" title="Baixar PowerPoint">
              <FileDown size={16} /> PPTX
            </button>
            <button onClick={() => downloadReport('pdf')} className="btn-report" title="Baixar PDF">
              <FileText size={16} /> PDF
            </button>
            <button onClick={() => downloadReport('html')} className="btn-report primary" title="Baixar Relatório Interativo">
              <LayoutDashboard size={16} /> Relatório Web
            </button>
            <button onClick={openPlotlyReport} className="btn-report" title="Visualização Dinâmica Plotly">
              <LayoutDashboard size={16} /> Gráfico Plotly
            </button>
            <button onClick={() => openFilterReport(2700, 2707)} className="btn-report" title="Filtrar OP 2700 / SUB_OP 2707">
              <LayoutDashboard size={16} /> 2700 / 2707
            </button>
          </div>
        )}
      </header>

      {!data && !uploadLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <label className="upload-card">
            <input type="file" hidden onChange={handleFileUpload} accept=".xlsx,.xls" />
            <Upload size={48} color="#4f46e5" style={{ animation: 'bounce 2s infinite' }} />
            <h2>Carregue sua planilha Excel</h2>
            <p>Clique ou arraste o arquivo .xlsx ou .xls para começar</p>
          </label>
          
          <button 
            onClick={loadDemo} 
            className="btn-report" 
            style={{ 
              alignSelf: 'center', 
              background: 'transparent', 
              border: '1px solid var(--primary)', 
              color: 'var(--primary)', 
              padding: '0.6rem 2.2rem' 
            }}
          >
            <Eye size={16} /> Ver Demonstração com Dados Fictícios
          </button>
        </div>
      ) : (
        <div className="dashboard-content">
          {/* Skeleton Loaders for KPIs and Charts during upload processing */}
          {uploadLoading ? (
            <div>
              <div className="dashboard-grid">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="stat-card">
                    <div className="skeleton skeleton-title"></div>
                    <div className="skeleton skeleton-value"></div>
                  </div>
                ))}
              </div>
              <div className="charts-grid">
                <div className="chart-container">
                  <div className="skeleton skeleton-title"></div>
                  <div className="skeleton skeleton-chart"></div>
                </div>
                <div className="chart-container">
                  <div className="skeleton skeleton-title"></div>
                  <div className="skeleton skeleton-chart"></div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {data === MOCK_DATA && (
                <div style={{ background: '#e0e7ff', color: '#4338ca', padding: '0.6rem 1.25rem', borderRadius: '0.75rem', marginBottom: '1.5rem', fontSize: '0.875rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Sparkles size={16} /> Modo de Demonstração Ativo
                </div>
              )}

              {/* KPIs Grid */}
              <div className="dashboard-grid">
                <div className="stat-card">
                  <h3>Valor Total</h3>
                  <div className="value">R$ {data.summary.total_value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                </div>
                <div className="stat-card">
                  <h3>Ticket Médio</h3>
                  <div className="value">R$ {data.summary.avg_transaction.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                </div>
                <div className="stat-card">
                  <h3>Fornecedores</h3>
                  <div className="value">{data.summary.count_suppliers}</div>
                </div>
                <div className="stat-card">
                  <h3>Transações</h3>
                  <div className="value">{data.summary.count_transactions}</div>
                </div>
              </div>

              {/* AI Insights Card */}
              {(insightsLoading || insights) && (
                <div className="insights-card">
                  <div className="insights-header" style={{ justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Sparkles size={20} color="var(--primary)" />
                      <h3>Insights Estratégicos (IA)</h3>
                    </div>
                    {!insightsLoading && (
                      <button 
                        onClick={fetchInsights} 
                        className="btn-report" 
                        style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                        title="Recarregar sugestões da IA"
                      >
                        <RefreshCw size={12} /> Recarregar
                      </button>
                    )}
                  </div>

                  {/* Audio Player Component */}
                  {!insightsLoading && insights && !isConfigError && (
                    <AudioPlayer 
                      text={playingSection ? playingSection.text : insights} 
                      sectionName={playingSection?.title}
                      onCloseSection={() => setPlayingSection(null)}
                      apiBase={API_BASE}
                    />
                  )}

                  <div className="insights-content">
                    {insightsLoading ? (
                      <div>
                        <div className="skeleton skeleton-text medium"></div>
                        <div className="skeleton skeleton-text"></div>
                        <div className="skeleton skeleton-text short"></div>
                      </div>
                    ) : (
                      parseMarkdown(insights)
                    )}
                  </div>
                </div>
              )}

              {/* Charts Grid */}
              <div className="charts-grid">
                <div className="chart-container">
                  <h3>Performance por Fornecedor (Top 10)</h3>
                  {supplierData && <Bar data={supplierData} options={{ responsive: true, plugins: { legend: { display: false } } }} />}
                </div>
                <div className="chart-container">
                  <h3>Tendência Temporal</h3>
                  {trendData && <Line data={trendData} options={{ responsive: true, plugins: { legend: { display: false } } }} />}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                <button onClick={() => { setData(null); setInsights(null); }} className="btn-report">
                  Carregar Novo Arquivo
                </button>
              </div>
            </>
          )}
        </div>
      )}
      </div>
    </>
  );
}

export default App;
