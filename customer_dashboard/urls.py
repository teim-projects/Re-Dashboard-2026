# your_app/urls.py
from django.urls import path
from . import views as local_views
from customer_dashboard import views as cd_views

urlpatterns = [
    # wind_dashboard appears to be in your local views (unchanged)
    path('wind_dashboard/', local_views.wind_dashboard, name="wind_dashboard"),
       
       
       
           # routes served by customer_dashboard.views
    path('wind_summary1/', cd_views.wind_summary1, name="wind_summary1"),
    path('wind_installation_summary2/', cd_views.wind_installation_summary2, name="wind_installation_summary2"),
    path('wind_generation_kwh/', cd_views.wind_generation_kwh, name="wind_generation_kwh"),
    path('wind_generation_hours/', cd_views.wind_generation_hours, name="wind_generation_hours"),
    path('wind_avg_genration/', cd_views.wind_avg_genration, name="wind_avg_genration"),
    path('wind_Grid_Availability_and_Machine/', cd_views.wind_Grid_Availability_and_Machine, name="wind_Grid_Availability_and_Machine"),
    path('wind_drill_down/', cd_views.wind_drill_down, name="wind_drill_down"),
    path('wind_breakdown_log/', cd_views.wind_breakdown_log, name="wind_breakdown_log"),
    path('wind_Avg_Machine_Availability/', cd_views.wind_Avg_Machine_Availability, name="wind_Avg_Machine_Availability"),
    path('customer_upload/', cd_views.customer_upload, name="customer_upload"),
    path('Modifydata/', cd_views.Modifydata, name="Modifydata"),
    path('wind_wtg_plf/', cd_views.wind_wtg_plf, name="wind_wtg_plf"),
    path('wind_Grid_Availability/', cd_views.wind_Grid_Availability, name="wind_Grid_Availability"),
    path('wind_breakdown_hours/', cd_views.wind_breakdown_hours, name="wind_breakdown_hours"),
    path("dsm_dashboard/",cd_views.dsm_dashboard, name="dsm_dashboard"),

    path('dashboard_breakdown', cd_views.dashboard_breakdown, name='dashboard_breakdown'),
 
    path("dsm_history/", cd_views.dsm_history, name="dsm_history"),
    path("export_dsm_history/", cd_views.export_dsm_history, name="export_dsm_history"),


    path('my_preventive_maintenance', cd_views.my_preventive_maintenance, name='my_preventive_maintenance'),
    path('user_completed_maintenance', cd_views.user_completed_maintenance, name='user_completed_maintenance'),
    path('user_pm_report_dashboard', cd_views.user_pm_report_dashboard, name='user_pm_report_dashboard'),
    path("breakdown_analysis", cd_views.breakdown_analysis, name="breakdown_analysis"),
    path("customer_upload_dsm", cd_views.customer_upload_dsm, name="customer_upload_dsm"),
path("email_breakdown_alerts/", cd_views.email_breakdown_alerts, name="email_breakdown_alerts"),

]