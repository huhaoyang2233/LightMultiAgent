import json
from datetime import datetime
import re

USE_MOCK_DB = True

mock_user_history = {}
mock_tool_history = {}

def query_history_message(userID, chatID, top=10):
    if USE_MOCK_DB:
        key = f"{userID}_{chatID}"
        history = mock_user_history.get(key, [])[-top:]
        return {
            "success": "1",
            "chat_history": history
        }
    
    try:
        import mysql.connector
        from config.settings import settings
        
        conn = mysql.connector.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_database,
            port=settings.db_port
        )
        cursor = conn.cursor()
        sql = """
            SELECT *
            FROM user_history_message
            WHERE user_id=%s AND chat_id=%s
            LIMIT %s
        """
        cursor.execute(sql, (userID, chatID, top))
        chat_history = []
        for row in cursor.fetchall():
            chat_history.append({
                "role": row[3],
                "content": row[6],
                "current_role": row[4],
            })
        conn.close()
        return {
            "success": "1",
            "chat_history": chat_history
        }
    except Exception as e:
        print(f"查询历史记录失败: {e}")
        return {
            "success": "1",
            "chat_history": []
        }

def get_sender_receiver(content):
    pattern_full = r"\[(.*?) -> (.*?)\]"
    match_full = re.search(pattern_full, content)
    if match_full:
        return {
            "sender": match_full.group(1),
            "receiver": match_full.group(2)
        }
    pattern_sender_only = r"\[(.*?)\]"
    match_sender = re.search(pattern_sender_only, content)
    if match_sender:
        return {
            "sender": match_sender.group(1),
            "receiver": ""
        }
    return {"sender": "", "receiver": ""}

def save_user_history_message(userID, chatID, current_history):
    if USE_MOCK_DB:
        key = f"{userID}_{chatID}"
        if key not in mock_user_history:
            mock_user_history[key] = []
        for item in current_history:
            if item["role"] != "tool":
                mock_user_history[key].append(item)
        print(f"模拟保存了 {len(current_history)} 条历史记录")
        return
    
    try:
        import mysql.connector
        from config.settings import settings
        
        conn = mysql.connector.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_database,
            port=settings.db_port
        )
        cursor = conn.cursor()
        sql = """
            INSERT INTO user_history_message 
            (user_id, chat_id, role, sender, receiver, content, create_time, update_time, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = []
        for item in current_history:
            if item["role"] == "tool":
                continue
            sr = get_sender_receiver(item["content"])
            sender = item["current_role"] if item["role"] == "assistant" else sr["sender"]
            receiver = sr["receiver"]
            values.append((
                userID, chatID, item["role"], sender, receiver,
                item["content"], datetime.now(), datetime.now(), "message_history"
            ))
        cursor.executemany(sql, values)
        conn.commit()
        conn.close()
        print(f"插入了 {cursor.rowcount} 条历史数据记录")
    except Exception as e:
        print(f"保存历史记录失败: {e}")

def save_tool_history_message(userID, chatID, role, tool_name, tool_input, tool_result):
    if USE_MOCK_DB:
        key = f"{userID}_{chatID}_tool"
        if key not in mock_tool_history:
            mock_tool_history[key] = []
        mock_tool_history[key].append({
            "user_id": userID,
            "chat_id": chatID,
            "role": role,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_result": tool_result,
            "create_time": datetime.now()
        })
        print(f"模拟保存了工具调用记录: {tool_name}")
        return
    
    try:
        import mysql.connector
        from config.settings import settings
        
        conn = mysql.connector.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_database,
            port=settings.db_port
        )
        cursor = conn.cursor()
        sql = """
            INSERT INTO tool_history_message 
            (user_id, chat_id, role, tool_name, tool_input, tool_result, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (userID, chatID, role, tool_name, tool_input, tool_result, datetime.now(), datetime.now()))
        conn.commit()
        conn.close()
        print(f"插入了工具调用记录")
    except Exception as e:
        print(f"保存工具调用记录失败: {e}")

def query_user_chats_history(userID, chatID):
    if USE_MOCK_DB:
        key = f"{userID}_{chatID}"
        history = mock_user_history.get(key, [])
        return {
            "success": "1",
            "chat_history": history
        }
    
    try:
        import mysql.connector
        from config.settings import settings
        
        conn = mysql.connector.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_database,
            port=settings.db_port
        )
        cursor = conn.cursor()
        sql = "SELECT * FROM user_history_message WHERE user_id=%s"
        
        def clear_content(content):
            return re.sub(r'\[.*?\]', '', content).strip()
        
        cursor.execute(sql, (userID,))
        chat_history = []
        for row in cursor.fetchall():
            chat_history.append({
                "user_id": row[1],
                "chat_id": row[2],
                "role": row[4],
                "receiver": row[5],
                "content": clear_content(row[6]),
                "timestamp": row[7]
            })
        conn.close()
        return {
            "success": "1",
            "chat_history": chat_history
        }
    except Exception as e:
        print(f"查询用户聊天历史失败: {e}")
        return {
            "success": "1",
            "chat_history": []
        }
