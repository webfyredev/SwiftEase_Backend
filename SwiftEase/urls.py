from django.urls import path
from .import views


urlpatterns = [
    path('contacts/', views.contactsViews, name='Contacts'),
    path('contacts-list/', views.contact_list, name='Contacts-list'),
    path('package/<str:code>/', views.package_trackingView, name='Track_Package'),
    path('package-list/', views.package_list, name='package-list'),
]
