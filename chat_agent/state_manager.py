from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any, Optional
import json
import re

class ChatRoomState:
    def __init__(self):
        self.chat_history: List[BaseMessage] = []
        self.current_role: str = ""
        self.user_id: str = ""
        self.chat_id: str = ""
        self.status: str = "debug"

    def add_message(self, message: BaseMessage):
        self.chat_history.append(message)

    def get_messages(self) -> List[BaseMessage]:
        return self.chat_history

    def clear(self):
        self.chat_history = []
        self.current_role = ""
        self.user_id = ""
        self.chat_id = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat_history": [msg.dict() for msg in self.chat_history],
            "current_role": self.current_role,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatRoomState":
        state = cls()
        state.current_role = data.get("current_role", "")
        state.user_id = data.get("user_id", "")
        state.chat_id = data.get("chat_id", "")
        state.status = data.get("status", "debug")
        
        for msg_data in data.get("chat_history", []):
            msg_type = msg_data.get("type", "")
            if msg_type == "human":
                state.chat_history.append(HumanMessage(**msg_data))
            elif msg_type == "ai":
                state.chat_history.append(AIMessage(**msg_data))
            elif msg_type == "system":
                state.chat_history.append(SystemMessage(**msg_data))
            elif msg_type == "tool":
                state.chat_history.append(ToolMessage(**msg_data))
        return state

class LangChainAgent:
    def __init__(self, model_name: str, api_key: str, base_url: str):
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            streaming=True
        )

    def generate_response(self, messages: List[BaseMessage], tools: Optional[List[Dict]] = None):
        if tools:
            return self.llm.bind_tools(tools).astream(messages)
        else:
            return self.llm.astream(messages)

    def generate_response_sync(self, messages: List[BaseMessage]) -> str:
        chain = self.llm | StrOutputParser()
        return chain.invoke(messages)

class RoleConfigLoader:
    @staticmethod
    def load_roles(config_path: str = "config/roles.json") -> Dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_role_config(roles: Dict[str, Any], role_name: str) -> Optional[Dict[str, Any]]:
        return roles.get("roles", {}).get(role_name)

    @staticmethod
    def get_call_out_tool(roles: Dict[str, Any], role_name: str, all_roles: Dict[str, Any]) -> Dict[str, Any]:
        tool = roles.get("call_out_tool", {}).copy()
        roles_description = "\n            ".join([
            f"- '{name}': {config['description']}" 
            for name, config in all_roles.items()
            if name != role_name
        ])
        if "function" in tool and "description" in tool["function"]:
            tool["function"]["description"] = tool["function"]["description"].replace(
                "{roles_description}", roles_description
            )
            tool["function"]["description"] = tool["function"]["description"].replace(
                "{current_role_name}", role_name
            )
        return tool

    @staticmethod
    def get_all_role_names(roles: Dict[str, Any]) -> List[str]:
        return list(roles.get("roles", {}).keys())

class MessageConverter:
    @staticmethod
    def to_langchain_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        result = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "user":
                result.append(HumanMessage(content=content))
            elif role == "assistant":
                result.append(AIMessage(content=content))
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                result.append(ToolMessage(content=content, tool_call_id=tool_call_id))
            else:
                result.append(HumanMessage(content=content))
        return result

    @staticmethod
    def from_langchain_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        result = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                result.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({
                    "role": "assistant", 
                    "content": msg.content,
                    "tool_calls": msg.tool_calls
                })
            elif isinstance(msg, ToolMessage):
                result.append({
                    "role": "tool", 
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id
                })
        return result

    @staticmethod
    def parse_tool_calls(response: AIMessage) -> List[Dict[str, Any]]:
        tool_calls = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_calls.append({
                    "function_name": tool_call["name"],
                    "arguments": tool_call["args"],
                    "tool_call_id": tool_call.get("id", "")
                })
        return tool_calls

    @staticmethod
    def extract_role_from_content(content: str) -> str:
        pattern = r"\[\s*([\w\-]+)\s*->\s*([\w\-]+)\s*\]"
        match = re.match(pattern, content)
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def extract_target_role_from_content(content: str) -> str:
        pattern = r"\[\s*([\w\-]+)\s*->\s*([\w\-]+)\s*\]"
        match = re.match(pattern, content)
        if match:
            return match.group(2)
        return ""

    @staticmethod
    def clean_content(content: str) -> str:
        pattern1 = r"\[\s*([\w\-]+)\s*->\s*([\w\-]+)\s*\]\s*"
        pattern2 = r"\[\s*([\w\-]+)\s*\]\s*"
        content = re.sub(pattern1, "", content)
        content = re.sub(pattern2, "", content)
        return content.strip()
