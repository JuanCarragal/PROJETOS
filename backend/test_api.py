from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_tts():
    response = client.post("/tts", json={"text": "Testando a API de áudio com FastAPI e síntese de voz neural."})
    print("TTS Status Code:", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Audio bytes length:", len(response.content))
    assert response.status_code == 200
    assert response.headers.get("content-type") == "audio/mpeg"
    assert len(response.content) > 1000
    print("Test API TTS Passed!")

if __name__ == "__main__":
    test_api_tts()
