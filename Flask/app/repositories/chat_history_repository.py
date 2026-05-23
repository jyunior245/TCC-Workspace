from app.extensions.sql_alchemy import db
from app.models.chat_history import ChatHistory

class ChatHistoryRepository:
    @staticmethod
    def get_recent_chats(user_id, limit=2):
        recent_chats = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(limit).all()
        return list(reversed(recent_chats))

    @staticmethod
    def save_chat(user_id, message, response, intent):
        new_chat = ChatHistory(user_id=user_id, message=message, response=response, intent=intent)
        db.session.add(new_chat)
        db.session.commit()
        return new_chat

    @staticmethod
    def get_chats_for_report(patient_id, start_time_utc, end_time_utc, updated_after=None):
        query = ChatHistory.query.filter(
            ChatHistory.user_id == patient_id,
            ChatHistory.timestamp >= start_time_utc,
            ChatHistory.timestamp <= end_time_utc
        )
        
        if updated_after:
            query = query.filter(ChatHistory.timestamp > updated_after)
            
        return query.order_by(ChatHistory.timestamp.asc()).all()

    @staticmethod
    def get_chats_for_context(patient_id, updated_after=None):
        query = ChatHistory.query.filter_by(user_id=patient_id).order_by(ChatHistory.timestamp.asc())
        
        if updated_after:
            query = query.filter(ChatHistory.timestamp > updated_after)
            
        return query.all()

    @staticmethod
    def delete_by_user_id(user_id):
        ChatHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()
