import mysql.connector
import uuid
from datetime import datetime

class DatabaseClient:
    def __init__(self):
        # Database connection details
        self.config = {
            'host': 'mobility-reporting.mysql.database.azure.com',
            'user': 'UserInternal_EdgarM',
            'password': '1bP1UNbzkr2Kz9Vz9uMneq9',
            'database': 'mobility_dfs_reports'
        }
        # This generates the unique string for the 'unique_reference' column
        self.unique_ref = str(uuid.uuid4())
        self.channel = "azure_openai_chat"
        self.adversarial_agent = "Edgar_adversarial_agent"

    def create_conversation_record(self):
        """Inserts the initial record into llm_conversations and returns the ID."""
        conn = mysql.connector.connect(**self.config)
        cursor = conn.cursor()
        query = """INSERT INTO llm_conversations 
                   (created_date_time, unique_reference, channel, adversarial_agent) 
                   VALUES (%s, %s, %s, %s)"""
        cursor.execute(query, (datetime.now(), self.unique_ref, self.channel, self.adversarial_agent))
        conv_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return conv_id

    def insert_message(self, role, message, conv_id):
        """Inserts a message into llm_messages and returns its auto-increment Id."""
        conn = mysql.connector.connect(**self.config)
        cursor = conn.cursor()
        query = """INSERT INTO llm_messages (role, message, conversation_id, created_date_time) 
                   VALUES (%s, %s, %s, %s)"""
        cursor.execute(query, (role, message, conv_id, datetime.now()))
        msg_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return msg_id

    def insert_evaluation(self, conv_id, msg_id, verdict, reason):
        """Inserts the audit result into llm_evaluator."""
        conn = mysql.connector.connect(**self.config)
        cursor = conn.cursor()
        query = """INSERT INTO llm_evaluator (unique_reference, conversation_id, verdict, message_id, reason) 
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (self.unique_ref, conv_id, verdict, msg_id, reason))
        conn.commit()
        cursor.close()
        conn.close()