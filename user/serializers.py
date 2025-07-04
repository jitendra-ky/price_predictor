from django.contrib.auth.models import User
from rest_framework import serializers

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}
    
    def validate_username(self, value):
        """
        Check that the username doesn't start with tg_ prefix (reserved for Telegram)
        """
        if value.startswith('tg_'):
            raise serializers.ValidationError(
                "Username cannot start with 'tg_' as this prefix is reserved for system use."
            )
        return value
    
    def create(self, validated_data):
        '''customize the create method as default on use wrong hash to set password'''
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
