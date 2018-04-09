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
#import all views in my_app
from my_app.views import *
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # DJANGO
    url(r'^login/', auth_views.login, name='login'),
    url(r'^admin/', admin.site.urls),
    # END OF DJANGO
    #
    # REGISTRATION
    url(r'^signup/$', signupView, name='signup'),
    url(r'^corporate/', corporateSignupView, name='Corporate Signup'),
    # END OF REGISTRATION
    #
    # PROFILE + WALLET
    url(r'^$', homeView, name='home'),
    url(r'^wallet/', walletView, name='wallet'),
    url(r'^cards/', addCardView, name='addCard'),
    url(r'^topup/', topupView, name='topup'),
    url(r'^withdraw/', withdrawView, name='withdraw'),
    url(r'^transfer/', transferView, name='transfer'),
    url(r'^exchange/', exchangeView, name='exchange'),
    url(r'^profile/', profileView, name='profile'),
    url(r'^uploadpic/', uploadPicView, name='uploadPic'),
    # END OF PROFILE + WALLET
    #
    # MESSAGES + NOTIFICATIONS + FRIENDS
    url(r'^search-friends/', usersView, name='users'),
    url(r'^add-friend/', addFriendView, name='add-friend'),
    url(r'^friends/', friendsView, name='friends'),
    url(r'^messages/', sendMessageView, name='message'),
    # END OF MESSAGES + NOTIFICATIONS + FRIENDS
    #
    # USER STORE + CART + STATS
    url(r'^buy/', buyProductView, name='Buy a Product'),
    url(r'^cart/', cartView, name='Your cart'),
    url(r'^checkout/', checkoutView, name='checkout'),
    url(r'^history/', historyView, name='history'),
    url(r'^monitor/', monthlyStatsView, name='monitor'),
    url(r'^explore/', exploreView, name='explore'),
    # END OF USER STORE + CART + STATS
    #
    # CORPORATE PRODUCTS AND STATS
    url(r'^sales/', salesView, name='Your Sales'),
    url(r'^products/', addProductView, name='Add Product'),
    url(r'^data/', corporateDataView, name='data'),
    url(r'^uploadfile/', uploadProductsView, name='Upload a File'),
    url(r'^campaign/', corporateCampaignView, name='Make a Campaign'),
    # END OF CORPORATE PRODUCTS AND status
    #
    # ETC.
    url(r'^logout/', logoutView, name='logout'),
    url(r'^rates/', viewRatesView, name='viewRates'),
    url(r'^settings/', settingsView, name='settings'),
    url(r'^terms/', termsView, name='terms'),
    # END OF ETC.
    #
    # JAVASCRIPT
    url(r'^get_notifications/', get_notifications_AJAX, name='get_notifications'),
    url(r'^notiflength/', get_notifications_length_AJAX, name='notiflength'),
    url(r'^messlength/', get_messages_length_AJAX, name='messlength'),
    url(r'^mark_as_clear/', mark_as_read_AJAX, name='mark_as_clear'),
    url(r'^send_message/', send_message_AJAX, name='message AJAX'),
    url(r'^get_messages/', get_messages_AJAX, name='get_messages'),
    url(r'^get-posts/', get_posts_AJAX, name='ajax posts'),
    url(r'^get-company-data/', get_company_data_AJAX, name="ajax company data"),
    # END OF JAVASCRIPT
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
