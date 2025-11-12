"""
Serializers pour l'API UserApp
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Connection, Post, Comment, Message, Notification


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle CustomUser
    """
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'avatar', 'headline', 'bio', 'location',
            'skills', 'education', 'experience', 'is_verified',
            'date_of_birth', 'date_joined', 'city', 'country', 'address',
            'role', 'is_active'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active']


class CustomUserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'utilisateur avec mot de passe
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label="Confirmer le mot de passe"
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Les mots de passe ne correspondent pas."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomUserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour du profil utilisateur
    """
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'phone', 'avatar',
            'headline', 'bio', 'location', 'skills',
            'education', 'experience', 'date_of_birth',
            'city', 'country', 'address'
        ]


class ConnectionSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Connection
    """
    from_user = CustomUserSerializer(read_only=True)
    to_user = CustomUserSerializer(read_only=True)
    from_user_id = serializers.IntegerField(write_only=True, required=False)
    to_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Connection
        fields = [
            'id', 'from_user', 'to_user', 'from_user_id', 'to_user_id',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        # Utiliser l'utilisateur connecté comme from_user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['from_user'] = request.user
        validated_data.pop('from_user_id', None)
        validated_data.pop('to_user_id', None)
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Post
    """
    author = CustomUserSerializer(read_only=True)
    author_id = serializers.IntegerField(write_only=True, required=False)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_id', 'content', 'media',
            'created_at', 'updated_at', 'comments_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_comments_count(self, obj):
        return obj.comments.count()

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['author'] = request.user
        validated_data.pop('author_id', None)
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Comment
    """
    author = CustomUserSerializer(read_only=True)
    author_id = serializers.IntegerField(write_only=True, required=False)
    post_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'post_id', 'author', 'author_id',
            'text', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['author'] = request.user
        validated_data.pop('author_id', None)
        return super().create(validated_data)


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Message
    """
    sender = CustomUserSerializer(read_only=True)
    receiver = CustomUserSerializer(read_only=True)
    sender_id = serializers.IntegerField(write_only=True, required=False)
    receiver_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'receiver', 'sender_id', 'receiver_id',
            'text', 'sent_at', 'read'
        ]
        read_only_fields = ['id', 'sent_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['sender'] = request.user
        validated_data.pop('sender_id', None)
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Notification
    """
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_id', 'verb', 'data',
            'read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data.pop('user_id', None)
        return super().create(validated_data)

