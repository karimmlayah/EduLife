from django.urls import path
from . import views

urlpatterns = [
    path('', views.evently_index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/submit/', views.forgot_password_submit_view, name='forgot_password_submit'),
    path('verify-reset-code/', views.verify_reset_code_view, name='verify_reset_code'),
    path('verify-reset-code/submit/', views.verify_reset_code_submit_view, name='verify_reset_code_submit'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('reset-password/submit/', views.reset_password_submit_view, name='reset_password_submit'),
    # New Account Settings URL (preferred)
    path('account-settings/', views.account_settings_view, name='account_settings'),
    path('account-settings/update/', views.profile_update_view, name='profile_update'),
    path('account-settings/change-password/', views.profile_change_password_view, name='profile_change_password'),
    # Backward-compatibility with old /profile/ URL (optional)
    path('profile/', views.profile_view, name='profile'),
    path('profile/update-public/', views.profile_update_public_view, name='profile_update_public'),
    path('profile/create-post/', views.create_post_view, name='create_post'),
    path('profile/post/<int:post_id>/update/', views.update_post_view, name='update_post'),
    path('profile/post/<int:post_id>/delete/', views.delete_post_view, name='delete_post'),
    # User profile and connections
    path('user/<int:user_id>/', views.user_profile_view, name='user_profile'),
    path('user/<int:user_id>/connect/', views.send_connection_request, name='send_connection'),
    path('connection/<int:connection_id>/accept/', views.accept_connection_request, name='accept_connection'),
    path('connection/<int:connection_id>/reject/', views.reject_connection_request, name='reject_connection'),
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    # Messages
    path('messages/', views.messages_view, name='messages'),
    path('messages/<int:user_id>/', views.messages_view, name='messages_conversation'),
    path('messages/<int:user_id>/send/', views.send_message_view, name='send_message'),
    path('messages/<int:message_id>/update/', views.update_message_view, name='update_message'),
    path('messages/<int:message_id>/delete/', views.delete_message_view, name='delete_message'),
    path('users/', views.manage_users_view, name='manage_users'),
    path('users/<int:user_id>/role/', views.set_user_role_view, name='set_user_role'),
    path('users/<int:user_id>/ban/', views.ban_user_view, name='ban_user'),
    path('users/<int:user_id>/unban/', views.unban_user_view, name='unban_user'),
    path('users/<int:user_id>/delete/', views.delete_user_view, name='delete_user'),
    path('api/face-id/register/', views.face_id_register, name='face_id_register'),
    path('api/face-id/authenticate/', views.face_id_authenticate, name='face_id_authenticate'),
    # Evently pages (explicit routes)
    path('about/', views.evently_template, {'page': 'about'}, name='evently_about'),
    path('fil-actualite/', views.schedule_view, name='evently_schedule'),
    path('speakers/', views.evently_template, {'page': 'speakers'}, name='evently_speakers'),
    path('speaker-details/', views.evently_template, {'page': 'speaker-details'}, name='evently_speaker_details'),
    path('venue/', views.evently_template, {'page': 'venue'}, name='evently_venue'),
    path('tickets/', views.evently_template, {'page': 'tickets'}, name='evently_tickets'),
    path('buy-tickets/', views.evently_template, {'page': 'buy-tickets'}, name='evently_buy_tickets'),
    path('gallery/', views.evently_template, {'page': 'gallery'}, name='evently_gallery'),
    path('terms/', views.evently_template, {'page': 'terms'}, name='evently_terms'),
    path('privacy/', views.evently_template, {'page': 'privacy'}, name='evently_privacy'),
    path('contact/', views.evently_template, {'page': 'contact'}, name='evently_contact'),
    path('sponsors/', views.evently_template, {'page': 'sponsors'}, name='evently_sponsors'),
    path('starter-page/', views.evently_template, {'page': 'starter-page'}, name='evently_starter_page'),
]
