from fastapi import FastAPI, Body
from kilo_v2.reasoning_engine import synthesize_answer, precompute_plugin_embeddings
from kilo_v2.plugin_manager import PluginManager
import uvicorn

app = FastAPI(title="Kilo Reasoning Microservice")
pm = PluginManager(plugin_dir="plugins")

@app.on_event("startup")
async def startup():
    await pm.load_plugins()
    precompute_plugin_embeddings(pm)

@app.post("/api/chat")
async def chat(query: str = Body(..., embed=True)):
    result = synthesize_answer(query, pm)
    return {"answer": result}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
