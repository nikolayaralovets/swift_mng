from django.urls import path, include
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('project/', views.project_list, name='project_list'),
    path('project/add/', views.project_add, name='project_add'),
    path('project/<str:pr>/', views.project_view, name='project_view'),
    path('project/<str:pr>/edit/', views.project_edit, name='project_edit'),
    path('project/delete/<str:prjid>/', views.project_delete, name='project_delete'),
    path('project/<str:pr>/useradd/', views.user_add, name='user_add'),
    path('project/<str:pr>/useredit/<str:usrid>/', views.user_edit, name='user_edit'),
    path('unassignrole/<str:prjid>/<str:usrid>/<str:roleid>/', views.user_unassign, name='user_unassign'),
    path('user/delete/<str:usr>/', views.user_delete, name='user_delete'),
    path('audit/', views.audit_log, name='audit_log'),
]
