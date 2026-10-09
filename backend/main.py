import os
import shutil
import re
import unicodedata
import pandas as pd
import plotly.express as px
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel
from typing import Optional
from .data_processor import DataProcessor
from .report_engine import ReportEngine
from .ai_service import AIService
from .tts_service import TTSService

app = FastAPI(title="Analytics Pro API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "backend/static/uploads"
REPORTS_DIR = "backend/reports"
AUDIO_DIR = "backend/static/audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Global variable to store last analyzed data and upload path (in a real app, use a DB or session)
last_analysis = None
last_uploaded_file = None
last_insights = None
tts_service = TTSService()

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "pt-BR-FranciscaNeural"

@app.post("/tts")
async def generate_tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    audio_bytes = await tts_service.synthesize(req.text, req.voice or "pt-BR-FranciscaNeural")
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Failed to synthesize audio.")
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"}
    )

@app.get("/insights/audio")
async def get_insights_audio(section: str = "all", voice: str = "pt-BR-FranciscaNeural"):
    global last_insights
    if last_insights is None:
        if last_analysis is not None:
            ai = AIService()
            last_insights = await ai.generate_insights(last_analysis)
        else:
            raise HTTPException(status_code=400, detail="No data or insights uploaded yet.")
    
    text_to_speak = tts_service.extract_section(last_insights, section)
    audio_bytes = await tts_service.synthesize(text_to_speak, voice)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Failed to synthesize insights audio.")
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"inline; filename=insights_{section}.mp3"}
    )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    processor = DataProcessor(file_path)
    if not processor.load_data():
        raise HTTPException(status_code=500, detail="Error processing the Excel file.")
    
    global last_analysis, last_uploaded_file, last_insights
    last_analysis = processor.get_all_analysis()
    last_uploaded_file = file_path
    last_insights = None
    return last_analysis
@app.get("/analysis")
async def get_analysis():
    if last_analysis is None:
        raise HTTPException(status_code=404, detail="No data uploaded yet.")
    return last_analysis
@app.get("/insights")
async def get_insights():
    global last_insights
    if last_analysis is None:
        raise HTTPException(status_code=400, detail="No data uploaded yet. Please upload an Excel file first.")
    
    if last_insights is not None:
        return {"insights": last_insights}
    
    ai = AIService()
    last_insights = await ai.generate_insights(last_analysis)
    return {"insights": last_insights}
@app.get("/reports/{report_type}")
async def generate_report(report_type: str):
    if last_analysis is None:
        raise HTTPException(status_code=404, detail="No data available for reporting.")
    
    engine = ReportEngine(last_analysis, last_insights)
    
    if report_type == "pptx":
        path = os.path.join(REPORTS_DIR, "report.pptx")
        engine.generate_pptx(path)
        return FileResponse(path, filename="Analytics_Pro_Report.pptx")
    
    elif report_type == "pdf":
        path = os.path.join(REPORTS_DIR, "report.pdf")
        engine.generate_pdf(path)
        return FileResponse(path, filename="Analytics_Pro_Report.pdf")
    
    elif report_type == "html":
        path = os.path.join(REPORTS_DIR, "report.html")
        engine.generate_html(path)
        return FileResponse(path, filename="Analytics_Pro_Report.html")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid report type.")
@app.get("/filter_report")
async def filter_report(op: int, sub_op: int, format: str = "json", file_path: str = None):
    """Return count and total value for rows matching op and sub_op.
    Query params:
      - op: operation code
      - sub_op: sub operation code
      - format: 'json' or 'html'
      - file_path: optional path to Excel file (defaults to project root attached file)
    """
    # Determine file to read
    try:
        target = file_path or os.path.join(os.getcwd(), "BASE GESTÃO - PROJETO 2700  2707.xlsx")
        # Use DataProcessor to leverage existing normalization
        processor = DataProcessor(target)
        if not processor.load_data():
            raise HTTPException(status_code=500, detail="Failed to load Excel file for filtering")
        df = processor.df
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Try to find OP, SUB_OP and VALOR columns robustly (handle renamed/normalized columns)
    def _normalize(s: str) -> str:
        s2 = unicodedata.normalize('NFKD', str(s))
        s2 = s2.encode('ascii', 'ignore').decode('ascii')
        s2 = re.sub(r'[^A-Za-z0-9]', '', s2).upper()
        return s2
    candidates_op = ['OP', 'OPERACAO', 'OPERAÇÃO', 'NU_OP']
    candidates_sub = ['SUB_OP', 'SUBOPERACAO', 'SUB OPERACAO', 'SUB_OPERAÇÃO']
    candidates_valor = ['VALOR', 'VALUE']
    norm_map = { _normalize(c): c for c in df.columns }
    op_col = None
    for cand in candidates_op:
        if _normalize(cand) in norm_map:
            op_col = norm_map[_normalize(cand)]; break
    sub_op_col = None
    for cand in candidates_sub:
        if _normalize(cand) in norm_map:
            sub_op_col = norm_map[_normalize(cand)]; break
    valor_col = None
    for cand in candidates_valor:
        if _normalize(cand) in norm_map:
            valor_col = norm_map[_normalize(cand)]; break
    if op_col is None or sub_op_col is None:
        raise HTTPException(status_code=400, detail="OP or SUB_OP columns not found in file")
    mask = (df[op_col] == op) & (df[sub_op_col] == sub_op)
    count = int(mask.sum())
    total = float(df.loc[mask, valor_col].sum()) if count > 0 and valor_col in df.columns else 0.0
    if format.lower() == 'html':
        html = f"<html><body><h1>Filter report</h1><p>OP: {op}</p><p>SUB_OP: {sub_op}</p><p>Count: {count}</p><p>Total: R$ {total:,.2f}</p></body></html>"
        return HTMLResponse(content=html)
    return {"op": op, "sub_op": sub_op, "count": count, "total_value": total}
def _normalize_column_name(column_name: str) -> str:
    normalized = unicodedata.normalize('NFKD', str(column_name))
    normalized = normalized.encode('ascii', 'ignore').decode('ascii')
    normalized = re.sub(r'[^A-Za-z0-9]', '', normalized).upper()
    return normalized
def _find_column(columns, candidates):
    norm = { _normalize_column_name(c): c for c in columns }
    for cand in candidates:
        key = _normalize_column_name(cand)
        if key in norm:
            return norm[key]
    return None
@app.get("/plotly_report")
async def plotly_report(file_path: str = None):
    target = file_path or last_uploaded_file or os.path.join(os.getcwd(), "BASE GESTÃO - PROJETO 2700  2707.xlsx")
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Excel source file not found")
    processor = DataProcessor(target)
    if not processor.load_data():
        raise HTTPException(status_code=500, detail="Failed to load Excel data for Plotly report")
    df = processor.df.copy()
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data available to plot")
    date_candidates = [
        'DATA_EMAIL', 'VENC_NF', 'DT_DISTRIBUICAO', 'DT_LANCAMENTO', 'DT_PAGAMENTO',
        'EMISSAO_Z', 'DATA', 'DATAEMAIL'
    ]
    valor_candidates = ['VALOR', 'VALUE']
    date_col = _find_column(df.columns, date_candidates)
    valor_col = _find_column(df.columns, valor_candidates)
    if date_col is None or valor_col is None:
        raise HTTPException(status_code=400, detail="Required date or value column not found")
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df[valor_col] = pd.to_numeric(df[valor_col], errors='coerce')
    df = df.dropna(subset=[date_col, valor_col])
    df = df.sort_values(by=date_col)
    fig = px.line(
        df,
        x=date_col,
        y=valor_col,
        title='Vendas ao longo do tempo',
        labels={date_col: 'Data', valor_col: 'Valor (R$)'},
        template='plotly_white'
    )
    fig.update_layout(
        title={'x': 0.5, 'xanchor': 'center'},
        xaxis_title='Data',
        yaxis_title='Valor (R$)',
        hovermode='x unified'
    )
    return HTMLResponse(content=fig.to_html(full_html=True, include_plotlyjs='cdn'))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)