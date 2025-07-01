from rest_framework import generics
from .serializers import RegisterSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated

class RegisterView(generics.CreateAPIView, generics.RetrieveAPIView):
    serializer_class = RegisterSerializer

    def get_permissions(self):
        """
        Allow anyone to register (POST),
        but only authenticated users can retrieve their data (GET).
        """
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_object(self):
        """
        For GET request, return the authenticated user.
        """
        return self.request.user
