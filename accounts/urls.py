from django.urls import path
from .views import *

urlpatterns = [
    path('register-user/', register_user, name="register_user"),
    path('login/', login_view, name="login"),
    path('logout/', logout_view, name='logout'),
    path('user-list/', user_list, name='user_list'),
    path('edit-user/<int:user_id>/', edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', delete_user, name='delete_user'),

    # ✅ New path to add Energy Type
    path('add-energy-type/', add_energy_type, name='add_energy_type'),       
    # ✅ Provider Master (newly added)
    path('add-provider/', add_provider_with_structure, name='add_provider'),

    path('existing-providers/',view_existing_providers, name='existing_providers'),
    path('add_dsm_structure/',add_dsm_structure, name='add_dsm_structure'),
    path('add_pm_structure/',add_pm_structure, name='add_pm_structure'),

]
