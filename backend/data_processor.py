import pandas as pd
import numpy as np
import re
import unicodedata
from typing import Dict, Any

class DataProcessor:
    COLUMN_ALIASES = {
        'valor': 'Valor',
        'fornecedor': 'Fornecedor',
        'operacao': 'Operação',
        'op': 'Operação',
        'suboperacao': 'Sub Operação',
        'sub_op': 'Sub Operação',
        'data': 'Data',
        'data_email': 'Data',
        'dt_lancamento': 'Data',
        'dt_distribuicao': 'Data',
        'dt_pagamento': 'Data',
        'dt_pag_025': 'Data',
        'venc_nf': 'Data',
    }

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.metrics = {}

    @staticmethod
    def _normalize_column(name: str) -> str:
        normalized = unicodedata.normalize('NFKD', str(name))
        normalized = normalized.encode('ascii', 'ignore').decode('ascii')
        normalized = re.sub(r'[^a-zA-Z0-9]+', '_', normalized).strip('_').lower()
        return normalized

    @classmethod
    def _normalized_columns(cls, columns):
        rename_map = {}
        used_targets = set()
        for col in columns:
            normalized = cls._normalize_column(col)
            canonical = cls.COLUMN_ALIASES.get(normalized)
            if canonical and canonical not in used_targets:
                rename_map[col] = canonical
                used_targets.add(canonical)
            else:
                rename_map[col] = col
        return rename_map

    def load_data(self):
        """Loads Excel data and performs initial cleanup."""
        try:
            self.df = pd.read_excel(self.file_path)
            self.df = self.df.rename(columns=self._normalized_columns(self.df.columns))
            # Ensure 'Data' is datetime
            if 'Data' in self.df.columns:
                self.df['Data'] = pd.to_datetime(self.df['Data'], errors='coerce')
            # Ensure 'Valor' is numeric
            if 'Valor' in self.df.columns:
                self.df['Valor'] = pd.to_numeric(self.df['Valor'], errors='coerce').fillna(0)
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    def get_executive_summary(self) -> Dict[str, Any]:
        """Calculates high-level metrics."""
        if self.df is None: return {}
        
        return {
            "total_value": float(self.df['Valor'].sum()),
            "avg_transaction": float(self.df['Valor'].mean()),
            "count_transactions": int(len(self.df)),
            "count_suppliers": int(self.df['Fornecedor'].nunique()) if 'Fornecedor' in self.df.columns else 0
        }

    def get_supplier_performance(self) -> Dict[str, Any]:
        """Analyzes top suppliers by value."""
        if self.df is None or 'Fornecedor' not in self.df.columns: return {}
        
        performance = self.df.groupby('Fornecedor')['Valor'].sum().sort_values(ascending=False).head(10)
        return performance.to_dict()

    def get_operational_breakdown(self) -> Dict[str, Any]:
        """Analyzes distribution by Operation and Sub Operation."""
        if self.df is None: return {}
        
        breakdown = {}
        if 'Operação' in self.df.columns:
            breakdown['by_operation'] = self.df.groupby('Operação')['Valor'].sum().to_dict()
        if 'Sub Operação' in self.df.columns:
            breakdown['by_sub_operation'] = self.df.groupby('Sub Operação')['Valor'].sum().to_dict()
        
        return breakdown

    def get_temporal_trends(self) -> Dict[str, Any]:
        """Analyzes value trends over time."""
        if self.df is None or 'Data' not in self.df.columns: return {}

        # Group by Month with fallback for older/newer pandas versions
        try:
            temporal = self.df.set_index('Data').resample('ME')['Valor'].sum()
        except (ValueError, TypeError):
            temporal = self.df.set_index('Data').resample('M')['Valor'].sum()
        return {str(k.date()): float(v) for k, v in temporal.to_dict().items()}

    def get_all_analysis(self) -> Dict[str, Any]:
        """Aggregates all analysis results."""
        return {
            "summary": self.get_executive_summary(),
            "suppliers": self.get_supplier_performance(),
            "operations": self.get_operational_breakdown(),
            "trends": self.get_temporal_trends()
        }
