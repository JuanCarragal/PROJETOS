import pandas as pd
from datetime import datetime, timedelta
import random

data = []
fornecedores = ["Tech Solutions", "Global Logistics", "Office Supply Co", "Alpha Services", "Beta Industries"]
operacoes = ["Compra", "Venda", "Devolução", "Transferência"]
sub_operacoes = ["Nacional", "Internacional", "Inter-estadual"]
produtos = ["Laptop Pro", "Cadeira Ergonômica", "Monitor 4K", "Teclado Mecânico", "Mouse Wireless"]
status = ["Concluído", "Pendente", "Cancelado"]
regioes = ["Sudeste", "Sul", "Norte", "Nordeste", "Centro-Oeste"]

start_date = datetime(2026, 1, 1)

for i in range(1, 51):
    data.append({
        "ID": i,
        "Data": start_date + timedelta(days=random.randint(0, 180)),
        "Fornecedor": random.choice(fornecedores),
        "Valor": round(random.uniform(100, 5000), 2),
        "Operação": random.choice(operacoes),
        "Sub Operação": random.choice(sub_operacoes),
        "Produto": random.choice(produtos),
        "Status": random.choice(status),
        "Vendedor": f"Vendedor {random.randint(1, 5)}",
        "Região": random.choice(regioes)
    })

df = pd.DataFrame(data)
df.to_excel("vendas_teste.xlsx", index=False)
print("Arquivo vendas_teste.xlsx gerado com sucesso!")
