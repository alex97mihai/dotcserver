"""myproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_views
# import all views in my_app
from my_app.views import *


urlpatterns = [
   # url(r'^$', HomeView.as_view()),
    url(r'^$', HomeView, name='home'),
    url(r'^signup/$', signup, name='signup'),
    url(r'^login/', auth_views.login, name='login'),
    url(r'^logout/', logoutView, name='logout'),
    url(r'^admin/', admin.site.urls),
 #   url(r'^hello/', HomeView.as_view()),
    url(r'^hello/', HomeView, name='helloHome'),
    url(r'^topup/', topup, name='topup'),
    url(r'^withdraw/', withdraw, name='withdraw'),
    url(r'^transfer/', transfer, name='transfer'),
    url(r'^rates/', viewRates, name='viewRates'),
    url(r'^exchange/', exchange, name='exchange'),
    url(r'^history/', historyView, name='history'),
    url(r'^search-friends/', users, name='users'),
    url(r'^add-friend/', addFriend, name='add-friend'),
    url(r'^friends/', friends, name='friends'),
    url(r'^notifications/', viewNotifications, name='notifications'),
    url(r'^get_notifications/', get_notifications, name='get_notifications'),
    url(r'^notiflength/', notiflength, name='notiflength'),

]
