from rest_framework import serializers
from .models import Contacts, Tracking_Package

class ContactsSerializers(serializers.ModelSerializer):
    class Meta:
        model = Contacts
        fields = "__all__"

class PackageSerializers(serializers.ModelSerializer):
    class Meta:
        model = Tracking_Package
        fields = "__all__"