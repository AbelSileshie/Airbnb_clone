from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, ValidationError
from .models import UserProfile

class RegisterSerializer(ModelSerializer):
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    address = serializers.CharField(max_length=255)
    age = serializers.IntegerField()
    phone_number = serializers.CharField(max_length=16, allow_blank=True, allow_null=True, required=False)
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, default='guest')

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'first_name', 'last_name', 'address', 'age', 'phone_number', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['password2']:
            raise ValidationError("Passwords do not match.")
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        UserProfile.objects.create(
            user=user,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            address=validated_data['address'],
            age=validated_data['age'],
            phone_number=validated_data.get('phone_number', None),
            role=validated_data.get('role', 'guest')
        )
        return user
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        data['user'] = user
        return data