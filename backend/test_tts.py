import asyncio
from backend.tts_service import TTSService

async def main():
    service = TTSService()
    test_md = """### Tendências Principais
- **Concentração de Gastos**: Os top 3 fornecedores respondem por mais de 60% do total.

### Recomendações Práticas
1. **Negociação de Volume**: Iniciar renegociação de prazos ou descontos imediatos.
2. **Diversificação**: Avaliar novos parceiros."""

    cleaned = service.clean_markdown(test_md)
    print("Cleaned markdown preview:", cleaned[:80])
    assert "###" not in cleaned
    assert "**" not in cleaned

    trends = service.extract_section(test_md, "trends")
    print("Extracted trends:", trends)
    assert "Concentração de Gastos" in trends

    recs = service.extract_section(test_md, "recommendations")
    print("Extracted recs:", recs)
    assert "Negociação de Volume" in recs

    print("Synthesizing audio with edge-tts...")
    audio = await service.synthesize("Olá! Este é um teste do player de voz neural para o sistema de relatórios.")
    print(f"Audio generated successfully: {len(audio)} bytes")
    assert len(audio) > 1000
    print("All TTSService tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
