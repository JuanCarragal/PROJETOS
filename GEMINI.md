# Instruções do Projeto (PROJETOS CLAUDE CODE)

Este arquivo serve como diretriz principal de contexto para qualquer agente ou assistente de IA executando neste workspace. Seu objetivo é otimizar a velocidade, eficiência de tokens e precisão das tarefas.

---

## 📂 Estrutura do Projeto

O projeto é dividido em duas partes principais:
1. **`backend/` (FastAPI / Python)**:
   - `main.py`: Ponto de entrada do servidor FastAPI.
   - `data_processor.py`: Processamento de dados e planilhas.
   - `report_engine.py`: Geração de relatórios (PDF/PPTX).
   - `static/uploads/`: Pasta de uploads temporários.
   - `reports/`: Pasta de saída para relatórios gerados.
2. **`frontend/` (React / TypeScript / Vite)**:
   - Estrutura SPA moderna com TypeScript.
   - Ponto de entrada em `src/main.tsx` e componente principal em `src/App.tsx`.

---

## ⚡ Diretrizes de Eficiência (Economia de Tokens e Velocidade)

Para garantir que as interações sejam extremamente rápidas e baratas em consumo de tokens, siga rigorosamente estas regras:

### 1. Descarte de Arquivos Irrelevantes (Ignorar)
- **NUNCA** escaneie ou leia arquivos dentro de `.venv/` ou `node_modules/`. Estes arquivos já estão mapeados nos arquivos `.geminiignore` e `.gitignore` na raiz.
- Se precisar realizar buscas (`grep_search` ou `glob`), utilize padrões inclusivos bem específicos (ex: `backend/**/*.py` ou `frontend/src/**/*.tsx`) para limitar o escopo.

### 2. Leituras Cirúrgicas (Surgical Reads)
- **Evite ler arquivos inteiros** se eles tiverem mais de 50 linhas.
- Utilize os parâmetros `start_line` e `end_line` do `read_file` para ler apenas o trecho necessário após identificar os locais de interesse usando `grep_search`.

### 3. Edições Cirúrgicas (Surgical Edits)
- **SEMPRE prefira a ferramenta `replace`** em vez de reescrever arquivos inteiros com `write_file`, a menos que seja um arquivo novo ou extremamente pequeno (menos de 30 linhas).
- Ao usar `replace`, forneça contexto suficiente de linhas anteriores e posteriores para garantir correspondência exata sem ambiguidade.

### 4. Execuções de Comandos Otimizadas
- Ao executar testes, linters ou servidores locais, use flags silenciosas (quiet flags) como `npm install --silent` ou execute comandos sem paginação para evitar saídas excessivamente longas no terminal que poluem o histórico de contexto.

---

## 🛠️ Tecnologias e Comandos Úteis

### Backend (Python):
- **Gerenciador de Pacotes / Ambiente**: `.venv\Scripts\python.exe`
- **Comando para Rodar o Servidor**: `.venv\Scripts\uvicorn backend.main:app --reload`

### Frontend (Node/React):
- **Gerenciador**: `npm` (executar comandos dentro da pasta `frontend/`)
- **Comando de Desenvolvimento**: `npm run dev`
- **Build**: `npm run build`
