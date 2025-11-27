"""
Планировщик задач для AI-агента
Автоматические проактивные сообщения клиентам
"""
import asyncio
import logging
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from models.user import User, Client
from ai_agent import sales_assistant
from notifications import notifier

logger = logging.getLogger(__name__)

class ProactiveMessenger:
    """Проактивные сообщения от AI-агента"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def analyze_and_message_clients(self):
        """
        Основная функция: анализ клиентов и отправка сообщений
        """
        logger.info("🤖 Starting proactive AI messaging...")
        
        db = SessionLocal()
        
        try:
            # Находим клиентов которым нужно написать
            clients_to_contact = await sales_assistant.find_clients_to_contact(db)
            
            logger.info(f"📊 Found {len(clients_to_contact)} clients to contact")
            
            messages_sent = 0
            
            for item in clients_to_contact:
                client = item['client']
                reason = item['reason']
                
                try:
                    # Получаем AI-анализ
                    logger.info(f"🔍 Analyzing client: {client.company_name}")
                    analysis = await sales_assistant.analyze_client(client, db)
                    
                    # Если AI говорит писать
                    if analysis.get('should_contact', False) and analysis.get('message'):
                        # Получаем telegram user
                        user = db.query(User).filter(User.id == client.user_id).first()
                        
                        if not user:
                            logger.warning(f"❌ User not found for client {client.id}")
                            continue
                        
                        # Отправляем сообщение
                        success = await notifier.send_message(
                            chat_id=user.telegram_id,
                            text=analysis['message']
                        )
                        
                        if success:
                            messages_sent += 1
                            logger.info(f"✅ Sent message to {client.company_name}")
                            
                            from models.ai_log import AIProactiveMessage
                            import json
                            
                            proactive_msg = AIProactiveMessage(
                                client_id=client.id,
                                reason=reason,
                                ai_analysis=json.dumps(analysis, ensure_ascii=False),
                                message_text=analysis['message']
                            )
                            db.add(proactive_msg)
                            db.commit()
                            logger.info(f"   Reason: {reason}")
                            logger.info(f"   AI timing: {analysis.get('timing', 'N/A')}")
                        else:
                            logger.error(f"❌ Failed to send message to {client.company_name}")
                        
                        # Задержка между сообщениями (чтобы не спамить)
                        await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing client {client.company_name}: {e}")
                    continue
            
            logger.info(f"🎉 Proactive messaging completed! Sent {messages_sent} messages")
            
        except Exception as e:
            logger.error(f"Error in proactive messaging: {e}")
        finally:
            db.close()
    
    async def test_run(self):
        """
        Тестовый запуск (вызывается вручную)
        """
        logger.info("🧪 TEST RUN: Proactive messaging")
        await self.analyze_and_message_clients()
    
    def start(self):
        """
        Запустить планировщик
        """
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        # Запускаем каждый день в 10:00 утра
        self.scheduler.add_job(
            self.analyze_and_message_clients,
            CronTrigger(hour=10, minute=0),
            id='proactive_messaging',
            name='AI Proactive Messaging',
            replace_existing=True
        )
        
        logger.info("📅 Scheduler configured: Daily at 10:00 AM")
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info("✅ Proactive messenger started!")
    
    def stop(self):
        """
        Остановить планировщик
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Proactive messenger stopped")

# Глобальный экземпляр
proactive_messenger = ProactiveMessenger()