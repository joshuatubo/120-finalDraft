from django.contrib import admin
from .models import Message
from .middleware import EncryptionMiddleware
import requests
from django.utils import timezone

# Register your models here.

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('receiver_email', 'encrypted_content', 'timestamp', 'is_delivered', 'is_read', 'read_timestamp')
    search_fields = ('receiver_email', 'encrypted_content')
    readonly_fields = ('timestamp', 'is_delivered', 'is_read', 'read_timestamp', 'encrypted_content')
    fields = ('receiver_email', 'content', 'encrypted_content', 'timestamp', 'is_delivered', 'is_read', 'read_timestamp')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('content',)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        try:
            # Set the sender
            obj.sender = request.user

            # Encrypt the message content with integrity check
            encryption = EncryptionMiddleware(None)
            encrypted_content = encryption.encrypt_message(obj.content)
            obj.encrypted_content = encrypted_content

            # Save the message
            super().save_model(request, obj, form, change)

            # Send message to receiver application
            receiver_url = 'http://localhost:8001/api/receive-message/'
            payload = {
                'sender_email': request.user.email,
                'receiver_email': obj.receiver_email,
                'encrypted_content': encrypted_content,
                'message_id': obj.id,
                'timestamp': timezone.now().isoformat()
            }
            
            print(f"Sending encrypted message to receiver: {payload}")
            
            response = requests.post(
                receiver_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                print(f"Message sent successfully: {response.json()}")
                obj.is_delivered = True
                obj.save()
            else:
                print(f"Error sending message: {response.text}")
                raise Exception(f"Failed to deliver message: {response.text}")
                
        except Exception as e:
            print(f"Error in save_model: {str(e)}")
            raise
