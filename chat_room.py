import backoff
from openai import APIConnectionError, APITimeoutError
import json
import random
import logging
import re
import time
import os

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.prompt_templates import PromptTemplates
from config.settings import settings
from chat_agent.state_manager import RoleConfigLoader

from history.Context_History import query_history_message
from history.Context_History import save_user_history_message
from history.Context_History import save_tool_history_message
from history.Context_History import query_user_chats_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("./logs/chat.log"),
        logging.StreamHandler()
    ]
)

class StockChatRoom:
    def __init__(self):
        self.max_iteration_steps = 5
        self.max_discussion_steps = 5+random.randint(0, 4)
        self.chat_history = []
        self.current_history = []
        self.userID = ""
        self.chatID = ""
        self.userTOKEN = ""
        self.target_role = ""
        self.query = ""
        self.status = ""
        
        self.roles_config = RoleConfigLoader.load_roles()
        self.all_roles = RoleConfigLoader.get_all_role_names(self.roles_config)
        
        # 初始化 管理员 LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model_name,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            streaming=True
        )
        
        # 初始化 角色 LLM
        self.agent_llm = ChatOpenAI(
            model=settings.llm_model_name,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            streaming=False
        )

    '''
        安全大模型调用
    '''
    @backoff.on_exception(backoff.expo, (APIConnectionError, APITimeoutError), max_tries=3)
    def safe_llm_chat(self, llm, messages):
        chain = llm
        return chain.invoke(messages)

    '''
        管理员 介入
    '''
    def chat_room_admin(self, target_role, query):
        if target_role and target_role in self.all_roles:
            logging.info(json.dumps({
                "event_type": "role_assignment",
                "context": f"直接指定角色: {target_role}"
            }, ensure_ascii=False))
            return target_role
        
        roles_description = "\n".join([
            f"{name}: {config['description']}" 
            for name, config in self.roles_config.get("roles", {}).items()
        ])
        
        admin_prompt = f"""
# 角色
你是一个群管理员，你身处一个股票聊天室，你负责发言用户指定

# 规则
- 当用户打招呼时你需要随机选择一个角色作为回应者，不能选择 Chat_User 作为回应者。
- 不能够选择当前发言的人，作为下一个发言对象
- 理解角色发言的用意，判断他这句话是对谁说的，同时需要判断输入的内容哪个角色可以完成这个任务
- []中包裹的是当前发言人的名字，你不能输出，你要另外选择下一个发言人

# 任务
根据输入的内容，从以下角色中选择唯一一个最合适的发言者：
{roles_description}

# 输出
你只能输出下一个发言的用户名，不能输出其他任何内容
# 例子：

PatternMaster
"""
        
        messages = [
            SystemMessage(content=admin_prompt),
            HumanMessage(content=f"#输入内容：{query}")
        ]
        
        response = self.safe_llm_chat(self.llm, messages)
        target_role = response.content.strip()
        self.target_role = target_role
        
        logging.info(json.dumps({
            "event_type": "role_assignment",
            "context": f"管理员指定角色: {target_role} 回答问题"
        }, ensure_ascii=False))
        
        return target_role

    '''
        聊天室入口
    '''
    def chat_room(self, data):
        user_config = data.get("user_config", {})
        user_message = data.get("user_message", {})
        self.userID = user_config.get("user_ID", "")
        self.chatID = user_config.get("chat_ID", "")
        self.userTOKEN = user_config.get("user_TOKEN", "")
        self.target_role = user_message.get("target_role", "")
        self.query = user_message.get("query", "")
        self.status = user_message.get("status", "debug")

        result = query_history_message(self.userID, self.chatID) or {}
        history = result.get("chat_history", [])
        self.chat_history = history[-15:]
        
        logging.info(json.dumps({
            "event_type": "context_injection",
            "context": f"注入全局上下文，历史消息数: {len(self.chat_history)}"
        }, ensure_ascii=False))

        target_role = self.chat_room_admin(self.target_role, "[Chat_User]" + self.query)
        
        save_user_history_message(self.userID, self.chatID, [{
            "role": "user",
            "content": "[Chat_User]" + self.query,
            "current_role": "Chat_User"
        }])
        
        user_ask = {
            "role": "user",
            "content": f"[Chat_User] {self.query}，大家一起讨论一下"
        }
        self.chat_history.append(user_ask)
        self.current_history.append(user_ask)
        
        logging.info(json.dumps({
            "event_type": "user_ask",
            "context": user_ask
        }, ensure_ascii=False))
        discussion_steps = 1
        warming_message=[]     #警告message用户指导agent工作
        max_warming_step=2
        warming_step=1 
        '''
            角色发言
        '''
        while self.target_role != "Chat_User" and discussion_steps <= self.max_discussion_steps and warming_step <= max_warming_step:
            current_role_name = self.target_role
            logging.info(json.dumps({
                "event_type": "role_speaking",
                "role": current_role_name,
                "discussion_step": discussion_steps
            }, ensure_ascii=False))
            
            current_role_config = RoleConfigLoader.get_role_config(self.roles_config, current_role_name)
            if not current_role_config:
                logging.warning(json.dumps({
                    "event_type": "role_not_found",
                    "role": current_role_name
                }, ensure_ascii=False))
                break

            call_out_tool = RoleConfigLoader.get_call_out_tool(
                self.roles_config,
                current_role_name,
                self.roles_config.get("roles", {})
            )
            tools = [call_out_tool] if call_out_tool else []
            '''
                过滤历史消息
            '''
            filtered_history = []
            for msg in self.chat_history:
                role = msg.get("role")
                current_role = msg.get("current_role")

                if role == "assistant" and current_role == current_role_name:
                    filtered_history.append(msg)
                elif role == "user" and current_role != current_role_name:
                    filtered_history.append(msg)
                elif role == "user" and current_role == current_role_name:
                    new_msg = msg.copy()
                    new_msg["role"] = "assistant"
                    filtered_history.append(new_msg)

            system_prompt = PromptTemplates.generate_system_prompt(current_role_config)
            
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(warming_message)
            for msg in filtered_history:
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

            try:
                if tools:
                    response = self.agent_llm.bind_tools(tools).invoke(messages)
                else:
                    response = self.agent_llm.invoke(messages)
                
                output = response.content or ""
                tool_calls = response.tool_calls or []
                
                logging.info(json.dumps({
                    "event_type": "agent_response",
                    "role": current_role_name,
                    "output_length": len(output),
                    "tool_calls": len(tool_calls)
                }, ensure_ascii=False))
                
                role_switch_triggered = False
                for tool_call in tool_calls:
                    warming_step=1
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    
                    logging.info(json.dumps({
                        "event_type": "tool_call",
                        "role": current_role_name,
                        "tool_name": tool_name,
                        "tool_args": tool_args
                    }, ensure_ascii=False))
                    '''
                        角色切换触发
                    '''
                    if tool_name == "call_out_tool":
                        target_role_name = tool_args.get("target_role_name", "")
                        content = tool_args.get("content", "")
                        
                        logging.info(json.dumps({
                            "event_type": "role_switch_triggered",
                            "from_role": current_role_name,
                            "to_role": target_role_name,
                            "content": content[:50] + "..." if len(content) > 50 else content
                        }, ensure_ascii=False))
                        
                        chunks = [content[i:i+200] for i in range(0, len(content), 200)]
                        for chunk in chunks:
                            yield f"data: {json.dumps({'role': current_role_name, 'content': chunk}, ensure_ascii=False)}\n\n"
                        
                        user_ask = {
                            "role": "user",
                            "content": f"[{current_role_name} -> {target_role_name}] {content}",
                            "current_role": current_role_name
                        }
                        self.chat_history.append(user_ask)
                        self.current_history.append(user_ask)
                        
                        save_user_history_message(self.userID, self.chatID, [user_ask])
                        
                        self.target_role = target_role_name
                        role_switch_triggered = True
                        break
                '''
                    角色发言
                '''
                if not role_switch_triggered:
                    if len(output) > 0:
                        warming_step=1
                        self.target_role = ""
                        pattern1 = r'^\[\s*([\w\-]+)\s*->\s*([\w\-]+)\s*\]'
                        pattern2 = r'^\[[^\]]*\]\s*'
                        
                        if re.match(pattern1, output):
                            match = re.match(pattern1, output)
                            clean_output = re.sub(pattern1, '', output).strip()
                            if match:
                                target = match.group(2)
                                if target != current_role_name:
                                    self.target_role = target
                                else:
                                    self.target_role = self.chat_room_admin(self.target_role, f"当前发言[{current_role_name}]" + clean_output + f"帮我指定一名说话角色，不可以是{current_role_name}")
                            content = f"[{current_role_name} -> {self.target_role}] {clean_output}"
                        elif re.match(pattern2, output):
                            match = re.match(pattern2, output)
                            clean_output = re.sub(pattern2, '', output).strip()
                            if match:
                                target = match.group(1)
                                if target != current_role_name:
                                    self.target_role = target
                                else:
                                    self.target_role = self.chat_room_admin(self.target_role, f"当前发言[{current_role_name}]" + clean_output + f"帮我指定一名说话角色，不可以是{current_role_name}")
                            content = f"[{current_role_name} -> {self.target_role}] {clean_output}"
                        else:
                            clean_output = output
                            if any(role in clean_output for role in self.all_roles):
                                mentioned_roles = [role for role in self.all_roles if role in clean_output]
                                non_chat_user_roles = [r for r in mentioned_roles if r != "Chat_User"]
                                if non_chat_user_roles:
                                    self.target_role = non_chat_user_roles[0]
                                else:
                                    self.target_role = mentioned_roles[0]
                                content = f"[{current_role_name} -> {self.target_role}] {clean_output}"
                            else:
                                self.target_role = self.chat_room_admin(self.target_role, f"当前发言:" + clean_output + f"帮我指定一名说话角色，如果发言中提到了用户名就是目标用户,不可以是{current_role_name}")
                                content = f"[{current_role_name} -> {self.target_role}] {clean_output}"
                        
                        chunks = [clean_output[i:i+200] for i in range(0, len(clean_output), 200)]
                        for chunk in chunks:
                            yield f"data: {json.dumps({'role': current_role_name, 'content': chunk}, ensure_ascii=False)}\n\n"

                        logging.info(json.dumps({
                            "event_type": "role_switch_triggered",
                            "from_role": current_role_name,
                            "to_role": self.target_role,
                            "content": content
                        }, ensure_ascii=False))
                        user_ask = {
                            "role": "user",
                            "content": content,
                            "current_role": current_role_name
                        }
                        self.chat_history.append(user_ask)
                        self.current_history.append(user_ask)
                        # current_role_message.append(user_ask)
                    else:
                        warming = {
                            "role": "user",
                            "content": "检测到异常，请根据分析结果发言！",
                            "current_role": self.target_role
                        }
                        warming_message=[]
                        warming_message.append(warming)
                        warming_step+=1
                        logging.warning(json.dumps({
                            "event_type": "empty_response",
                            "role": current_role_name,
                            "warning": "检测到空响应"
                        }, ensure_ascii=False))
                        continue
            
            except Exception as e:
                logging.error(json.dumps({
                    "event_type": "agent_error",
                    "role": current_role_name,
                    "error": str(e)
                }, ensure_ascii=False))
                
                yield f"data: {json.dumps({'role': current_role_name, 'content': f'发言时发生错误: {str(e)}'}, ensure_ascii=False)}\n\n"
                break
            '''
                角色发言
            '''
            if output:
                self.chat_history.append({
                    "role": "assistant",
                    "content": output,
                    "current_role": current_role_name
                })
                
                save_user_history_message(self.userID, self.chatID, [{
                    "role": "assistant",
                    "content": output,
                    "current_role": current_role_name
                }])
            
            discussion_steps += 1
            logging.info(json.dumps({
                "event_type": "discussion_step_complete",
                "step": discussion_steps,
                "current_role": self.target_role
            }, ensure_ascii=False))
        
        return