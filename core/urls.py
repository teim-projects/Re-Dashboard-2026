from django.urls import path
from .views import *
from django.urls import include
urlpatterns = [
    # Default index
    path('', index_page, name="index"),

    # Dashboard routing
    path('dashboard/', dashboard, name='dashboard'),          # 👈 add this
    path('wind-dashboard/', dashboard, name='wind_dashboard'),
    path('biogas-dashboard/', dashboard, name='biogas_dashboard'),

    # Upload and Modify
    path('upload-files/', upload_files, name='upload_files'),
    path('modify-data/', modify_data, name="modify_data"),

    # User management
    path('manage-users/', manage_user, name='manage_users'),

    # Client Information
    path('client-info/', client_info, name="client_info"),
    path('user_generation_info/', user_generation_info, name="user_generation_info"),

    # Installation Summary & Data Uploads
    path('upload-installation-summary/', upload_installation_summary, name='upload_installation_summary'),
    path('upload-installation-data/', upload_installation_data, name='upload_installation_data'),

    # Template Download
    path('download-template/', download_template, name='download_template'),

    # Include account app routes
    path('accounts/', include('accounts.urls')),
    path('manage-installation/', manage_installation_data, name='manage_installation_data'),
    path('tracking_dashboard', tracking_dashboard, name='tracking_dashboard'),
    path('upload_preventive_maintenance', upload_preventive_maintenance, name='upload_preventive_maintenance'),
    path('manage_preventive_maintenance', manage_preventive_maintenance, name='manage_preventive_maintenance'),
    path('upload_dsm_data', upload_dsm_data, name='upload_dsm_data'),
    path('delete_dsm_data', delete_dsm_data, name='delete_dsm_data'),
    
]
