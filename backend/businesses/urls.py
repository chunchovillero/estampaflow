from django.urls import path
from .views import BusinessSettingView,CurrentBusinessView,CurrentPlanView,MemberDetailView,MemberListCreateView,PlatformPlanView,TerritoryView

urlpatterns=[path("territories/",TerritoryView.as_view()),path("current/",CurrentBusinessView.as_view()),path("plan/",CurrentPlanView.as_view()),path("platform/plans/",PlatformPlanView.as_view(http_method_names=["get","head","options"])),path("platform/plans/<int:pk>/",PlatformPlanView.as_view(http_method_names=["patch","options"])),path("settings/",BusinessSettingView.as_view()),path("members/",MemberListCreateView.as_view()),path("members/<int:pk>/",MemberDetailView.as_view())]
