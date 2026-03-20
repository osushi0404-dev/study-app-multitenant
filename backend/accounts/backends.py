from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailOrUserIdBackend(BaseBackend):
    """
    Custom authentication backend that allows users to login with either email or user_id
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            # Try to find user by email or user_id
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(user_id=username)
                
            # Check password
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None