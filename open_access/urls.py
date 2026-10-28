from django.urls import path
from . import views
from django.urls import include

urlpatterns = [

    # path('open-access/',views.open_access,name='open_access')
    path('', views.open_access, name='open_access'),
    path("calculator/", views.calculator_view, name="calculator"),
    path('calculation_history', views.calculation_history, name='calculation_history'),
    path('history/delete/<int:pk>/', views.delete_record, name='delete_record'),

    path("history/details/<int:pk>/", views.record_details, name="record_details"),

]