"""
WebSocket consumers for real-time notifications, chat, and admin dashboard.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Notification
from issues.models import Issue, Comment
from accounts.models import User


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time notifications."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        
        self.user = self.scope["user"]
        self.user_group_name = f"user_{self.user.id}"
        
        # Join user group for personal notifications
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send unread notifications on connect
        await self.send_unread_notifications()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def send_unread_notifications(self):
        """Send unread notifications to the user."""
        notifications = await self.get_unread_notifications()
        
        for notification in notifications:
            await self.send(text_data=json.dumps({
                'type': 'notification',
                'notification': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'notification_type': notification.notification_type,
                    'created_at': notification.created_at.isoformat(),
                    'is_read': notification.is_read
                }
            }))
    
    async def notification_message(self, event):
        """Handle notification message."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Get unread notifications for the user."""
        return list(Notification.objects.filter(
            user=self.user,
            is_read=False
        ).order_by('-created_at')[:10])


class ChatConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time chat on issues."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        
        self.user = self.scope["user"]
        self.issue_id = self.scope['url_route']['kwargs']['issue_id']
        self.issue_group_name = f"issue_{self.issue_id}"
        
        # Check if user has access to this issue
        if not await self.can_access_issue():
            await self.close()
            return
        
        # Join issue group
        await self.channel_layer.group_add(
            self.issue_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send recent chat history
        await self.send_chat_history()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.issue_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming chat message."""
        try:
            data = json.loads(text_data)
            message = data['message']
            
            # Save message to database
            comment = await self.save_comment(message)
            
            # Broadcast message to all users in the issue
            await self.channel_layer.group_send(
                self.issue_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': comment.id,
                        'content': comment.content,
                        'author': {
                            'id': comment.author.id,
                            'email': comment.author.email,
                            'first_name': comment.author.first_name,
                            'last_name': comment.author.last_name
                        },
                        'created_at': comment.created_at.isoformat(),
                        'is_staff': comment.author.is_staff
                    }
                }
            )
        except (json.JSONDecodeError, KeyError):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))
    
    async def chat_message(self, event):
        """Handle chat message broadcast."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    @database_sync_to_async
    def can_access_issue(self):
        """Check if user can access the issue."""
        try:
            issue = Issue.objects.get(id=self.issue_id)
            return (
                self.user.is_staff or 
                issue.author == self.user or 
                issue.assigned_to == self.user
            )
        except Issue.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_comment(self, message):
        """Save comment to database."""
        issue = Issue.objects.get(id=self.issue_id)
        return Comment.objects.create(
            issue=issue,
            author=self.user,
            content=message
        )
    
    @database_sync_to_async
    def get_chat_history(self):
        """Get recent chat history."""
        comments = Comment.objects.filter(
            issue_id=self.issue_id
        ).order_by('created_at')[:50]
        
        return [{
            'id': comment.id,
            'content': comment.content,
            'author': {
                'id': comment.author.id,
                'email': comment.author.email,
                'first_name': comment.author.first_name,
                'last_name': comment.author.last_name
            },
            'created_at': comment.created_at.isoformat(),
            'is_staff': comment.author.is_staff
        } for comment in comments]
    
    async def send_chat_history(self):
        """Send chat history to the user."""
        history = await self.get_chat_history()
        
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': history
        }))


class AdminDashboardConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time admin dashboard updates."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        user = self.scope["user"]
        role = getattr(user, "role", None)
        if not (user.is_superuser or role == "admin"):
            await self.close()
            return
        
        self.admin_group_name = "admin_dashboard"
        
        # Join admin group
        await self.channel_layer.group_add(
            self.admin_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial dashboard data
        await self.send_dashboard_data()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.admin_group_name,
            self.channel_name
        )
    
    async def dashboard_update(self, event):
        """Handle dashboard update broadcast."""
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))
    
    async def send_dashboard_data(self):
        """Send current dashboard statistics."""
        stats = await self.get_dashboard_stats()
        
        await self.send(text_data=json.dumps({
            'type': 'dashboard_data',
            'data': stats
        }))
    
    @database_sync_to_async
    def get_dashboard_stats(self):
        """Get dashboard statistics."""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        return {
            'total_issues': Issue.objects.count(),
            'open_issues': Issue.objects.filter(status='open').count(),
            'in_progress_issues': Issue.objects.filter(status='in_progress').count(),
            'resolved_issues': Issue.objects.filter(status='resolved').count(),
            'issues_last_24h': Issue.objects.filter(created_at__gte=last_24h).count(),
            'issues_last_7d': Issue.objects.filter(created_at__gte=last_7d).count(),
            'total_users': User.objects.count(),
            'active_users_last_24h': User.objects.filter(
                last_login__gte=last_24h
            ).count(),
            'urgent_issues': Issue.objects.filter(priority='urgent', status__in=['open', 'in_progress']).count(),
        }
