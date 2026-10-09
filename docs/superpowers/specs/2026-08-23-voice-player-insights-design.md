# Especificação de Design: Player de Voz Neural para Insights & Recomendações

**Data:** 2026-08-23  
**Status:** Aprovado pelo Usuário  
**Objetivo:** Adicionar funcionalidade de Text-to-Speech (TTS) com vozes neurais realistas em português brasileiro e um player de áudio interativo moderno para reproduzir os insights e recomendações práticas gerados pela IA no dashboard.

---

## 1. Visão Geral e Requisitos

### 1.1 Objetivo do Usuário
Permitir que o usuário ouça os relatórios analíticos, tendências e recomendações práticas gerados pela IA, aumentando a acessibilidade, dinamismo e conveniência durante a análise de dados.

### 1.2 Requisitos Funcionais
1. **Geração de Áudio Neural**:
   - Geração de áudio com vozes neurais em Português do Brasil (`pt-BR-FranciscaNeural` e `pt-BR-AntonioNeural`) via backend sem custos de chaves de API.
   - Endpoint dedicado `POST /tts` e `GET /insights/audio` no FastAPI.
   - Cache em disco para áudios já sintetizados para evitar regenerações repetidas.
2. **Player de Áudio no Frontend**:
   - Player principal moderno integrado ao card de Insights.
   - Controles: Play, Pause, Retomar, Parar, Barra de Progresso com seek/arrasto, Tempo atual / Duração total, Controle de Velocidade (1.0x, 1.25x, 1.5x, 2.0x), Volume / Mute, Download do áudio em MP3.
   - Efeito visual de ondas de áudio pulsantes enquanto estiver tocando.
3. **Reprodução Granular por Seções**:
   - Botões de reprodução rápida em cada bloco de conteúdo (ex: botão para ouvir apenas "Tendências Principais" ou apenas "Recomendações Práticas").
4. **Resiliência e Modo Demonstração**:
   - Suporte transparente no modo de demonstração do frontend.
   - Fallback para Web Speech API do navegador caso o backend esteja indisponível.

---

## 2. Arquitetura Técnica

### 2.1 Backend (FastAPI / Python)
- **Biblioteca de TTS**: `edge-tts` (assíncrono, alta performance, vozes neurais Microsoft).
- **Módulo de TTS (`backend/tts_service.py`)**:
  - `TTSService`: classe responsável por converter texto limpo (sem tags markdown excessivas) em áudio MP3.
  - Método `synthesize(text: str, voice: str = "pt-BR-FranciscaNeural") -> bytes`.
  - Método para limpar Markdown antes de sintetizar (remoção de `#`, `*`, URLs, etc., preservando a fluidez da fala).
- **Endpoints no `backend/main.py`**:
  - `POST /tts`: recebe `{ "text": str, "voice": Optional[str] }` e retorna stream `audio/mpeg`.
  - `GET /insights/audio?section={all|trends|recommendations}`: sintetiza e retorna o áudio do insight armazenado no servidor.
- **Armazenamento de Cache**: `backend/static/audio/` para arquivos temporários.

### 2.2 Frontend (React + TypeScript)
- **Componente de Áudio Dedicado (`frontend/src/components/AudioPlayer.tsx`)**:
  - Encapsula a tag HTML5 `<audio>` com estado gerenciado (isPlaying, currentTime, duration, playbackRate, volume, isBuffering).
  - Interface customizada com CSS sofisticado (gradientes, glassmorphism, micro-animações, botões de ação rápida).
- **Integração no `frontend/src/App.tsx`**:
  - Renderiza o `AudioPlayer` no topo do container de `insights`.
  - Adiciona botões "Ouvir Seção" adjacentes aos títulos `### Tendências Principais` e `### Recomendações Práticas`.
  - Tratamento de erro elegante com fallback para áudio nativo caso a chamada HTTP falhe.

---

## 3. Experiência de Uso (UX) e Acessibilidade

1. **Carregamento e Feedback**:
   - Enquanto o áudio é sintetizado pelo backend, o botão exibe um spinner suave de carregamento ("Gerando áudio...").
2. **Destaque Visual**:
   - A seção que está sendo reproduzida ganha um leve destaque visual (glow / borda sutil) para guiar os olhos do usuário.
3. **Download**:
   - O usuário pode baixar o arquivo `.mp3` dos insights para compartilhar ou ouvir offline.

---

## 4. Plano de Verificação

1. **Testes do Backend**:
   - Testar endpoint `POST /tts` com texto de teste em português e verificar retorno do mimetype `audio/mpeg` com dados binários válidos.
   - Testar endpoint `/insights/audio` com o conteúdo retornado pela IA.
2. **Testes do Frontend**:
   - Verificar renderização do player no modo de demonstração e no modo com upload de arquivo real.
   - Testar controles de Play, Pause, Seek na barra de progresso, alteração de velocidade e download.
   - Testar reprodução individual da seção de "Recomendações Práticas".
