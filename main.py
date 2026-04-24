from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import logging

from chat_room import StockChatRoom
from history.Context_History import query_user_chats_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("./logs/chat.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI(title="Stock Chat Room API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserConfig(BaseModel):
    user_ID: str
    chat_ID: str
    user_TOKEN: Optional[str] = ""

class UserMessage(BaseModel):
    target_role: Optional[str] = ""
    query: str

class ChatRequest(BaseModel):
    user_config: UserConfig
    user_message: UserMessage
    status: Optional[str] = "debug"

class HistoryRequest(BaseModel):
    userID: str
    chatID: Optional[str] = "chat_ID"

chatroom = StockChatRoom()

'''
    聊天API
'''
@app.post("/chat")
async def chat(request: ChatRequest):
    logging.info(json.dumps({
        "event_type": "user_input",
        "context": request.dict()
    }, ensure_ascii=False))
    
    data = {
        "user_config": request.user_config.dict(),
        "user_message": request.user_message.dict(),
        "status": request.status
    }
    
    def generate():
        for message in chatroom.chat_room(data):
            yield message
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/chat_stream")
async def chat_stream(user_ID: str, chat_ID: str, query: str, target_role: Optional[str] = "", status: Optional[str] = "debug"):
    logging.info(json.dumps({
        "event_type": "user_input",
        "context": {
            "user_ID": user_ID,
            "chat_ID": chat_ID,
            "query": query,
            "target_role": target_role,
            "status": status
        }
    }, ensure_ascii=False))
    
    data = {
        "user_config": {
            "user_ID": user_ID,
            "chat_ID": chat_ID,
            "user_TOKEN": ""
        },
        "user_message": {
            "target_role": target_role,
            "query": query
        },
        "status": status
    }
    
    def generate():
        for message in chatroom.chat_room(data):
            yield message
    
    return StreamingResponse(generate(), media_type="text/event-stream")

'''
    历史消息API
'''
@app.post("/chat/history")
async def get_history_message(request: HistoryRequest):
    result = query_user_chats_history(request.userID, request.chatID)
    return result

'''
    健康检查API
'''
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Stock Chat Room"}

if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
        workers=1
    )
