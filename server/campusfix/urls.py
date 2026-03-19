from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('issues.urls')),
    path('api/', include('notifications.urls')),
    path('admin/', include('issues.admin_urls', namespace='issues')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
]

def verification_redirect(request, token):
    target_url = f"{settings.SITE_URL}/auth/verify-email/{token}/"
    if target_url == request.build_absolute_uri():
        return HttpResponse(
            f"Circular redirect detected. SITE_URL is set to {settings.SITE_URL}, "
            "which is the same as the backend. Please check your .env file and "
            "set SITE_URL to point to your frontend (e.g., http://localhost:5173).",
            status=400
        )
    return redirect(target_url)

urlpatterns += [
    # Redirect to frontend for email verification links that might use the backend port
    path('auth/verify-email/<str:token>/', verification_redirect),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
