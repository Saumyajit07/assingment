from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.contrib.auth import authenticate
from .models import CustomUser, FriendRequest
from .serializers import UserSerializer, FriendRequestSerializer
from django.db.models import Q
from rest_framework.throttling import UserRateThrottle
from rest_framework.pagination import PageNumberPagination

class CustomUserThrottle(UserRateThrottle):
    rate = '3/minute'

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['email', 'first_name', 'last_name']
    
    def get_permissions(self):
        if self.action in ['signup', 'login']:
            self.permission_classes= [AllowAny]
        else:
            self.permission_classes= [IsAuthenticated]
        return super(UserViewSet, self).get_permissions()

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')

        print(f"Search query: {query}")  # Debugging statement
        
        if '@' in query:
            users = CustomUser.objects.filter(email__iexact=query)
        else:
            users = CustomUser.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )

        print(f"Found users: {users}")  # Debugging statement
        
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(users, request)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get('email').lower()
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key})
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def signup(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
        user = CustomUser.objects.create_user(email=email, password=password)
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})

class FriendRequestViewSet(viewsets.ModelViewSet):
    queryset = FriendRequest.objects.all()
    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomUserThrottle]

    def perform_create(self, serializer):
        to_user = serializer.validated_data.get('to_user')
        if to_user == self.request.user:
            raise serializer.ValidationError("You can't send a friend request to yourself.")
        serializer.save(from_user=self.request.user)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        user = request.user
        pending_requests = FriendRequest.objects.filter(to_user=user, status='pending')
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def friends(self, request):
        user = request.user
        friends = CustomUser.objects.filter(
            Q(sent_requests__to_user=user, sent_requests__status='accepted') |
            Q(received_requests__from_user=user, received_requests__status='accepted')
        ).distinct()
        serializer = UserSerializer(friends, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        friend_request = self.get_object()
        if friend_request.to_user != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        friend_request.status = 'accepted'
        friend_request.save()
        return Response({'status': 'Request accepted'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        friend_request = self.get_object()
        if friend_request.to_user != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        friend_request.status = 'rejected'
        friend_request.save()
        return Response({'status': 'Request rejected'})
