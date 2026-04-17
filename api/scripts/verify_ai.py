import asyncio
import base64
import httpx
import sys
import os

# Add the api directory to the path so we can import app modules
sys.path.append(os.path.join(os.getcwd(), "api"))

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.vision_service import vision_service
from app.config import settings

async def test_chat():
    print("\n--- Testing Chat (Classification) ---")
    message = "How much to install a 50 gallon electric water heater in Dallas?"
    print(f"Query: {message}")
    
    result = await llm_service.classify(message)
    if result:
        print(f"✅ Success! Classification: {result['task_code']} (Confidence: {result['confidence']})")
    else:
        print("❌ Failed to classify message.")

async def test_embedding():
    print("\n--- Testing Embeddings (RAG) ---")
    text = "Plumbing code requirements for water heater pan drainage."
    print(f"Text: {text}")
    
    vector = await rag_service.embed(text)
    if vector and len(vector) > 0:
        print(f"✅ Success! Generated vector with {len(vector)} dimensions.")
    else:
        print("❌ Failed to generate embedding.")

async def test_vision():
    print("\n--- Testing Vision (Blueprints) ---")
    # Force override for test if not picking up env
    settings.llm_vision_model = "minicpm-o2.6:latest"
    
    # Using a tiny 1x1 transparent PNG as a placeholder to test API connectivity
    placeholder_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    
    from app.services.vision_service import VisionService
    vs = VisionService()
    
    model = settings.llm_vision_model
    print(f"Model: {model}")
    print(f"Endpoint: {vs.endpoint}")
    print("Sending placeholder image to Ollama...")
    
    result = await vs.classify_sheet(placeholder_png)
    if result and result.get("sheet_type") != "unknown":
        print(f"✅ Success! Vision response: {result.get('sheet_type', 'unknown')}")
    elif result:
        print(f"⚠️ Vision connected but returned unknown (expected for placeholder): {result}")
    else:
        print("❌ Vision classification failed.")

async def main():
    print(f"Verifying AI Services at {settings.hermes_endpoint_url}")
    print(f"Environment: {settings.environment}")
    
    try:
        await test_chat()
        await test_embedding()
        await test_vision()
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
