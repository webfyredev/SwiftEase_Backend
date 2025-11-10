from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import ContactsSerializers, PackageSerializers
from .models import Contacts, Tracking_Package

@api_view(['POST'])
def contactsViews(request):
    serializers = ContactsSerializers(data=request.data)
    if serializers.is_valid():
        serializers.save()
        return Response({'message' : 'Data submitted successfully'}, status=status.HTTP_201_CREATED)
    return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def contact_list(request):
    contacts = Contacts.objects.all()
    serializer = ContactsSerializers(contacts, many=True, context={'request' : request})
    return Response(serializer.data)

@api_view(['GET'])
def package_trackingView(request, code):
    package = Tracking_Package.objects.get(tracking_code=code)
    serializers = PackageSerializers(package, context={'request' : request})
    return Response(serializers.data)

@api_view(['GET'])
def package_list(request):
    package = Tracking_Package.objects.all().order_by('-last_updated')
    serializers = PackageSerializers(package, many=True, context={'request' : request})
    return Response(serializers.data)