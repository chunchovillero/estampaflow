from django.urls import path
from .views import BusinessSettingView,CurrentBusinessView,MemberDetailView,MemberListCreateView

urlpatterns = [path("current/", CurrentBusinessView.as_view()),path("settings/",BusinessSettingView.as_view()),path("members/", MemberListCreateView.as_view()), path("members/<int:pk>/", MemberDetailView.as_view())]
