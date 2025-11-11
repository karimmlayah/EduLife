from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import Http404
from UserApp.models import CustomUser

# Create your views here.
def logement_home(request):
    return render(request, 'instructors.html')


@login_required
def dashboard(request):
    return render(request, 'Backoffice/dashboard.html')


@login_required
def argon_page(request, page: str):
    allowed = {
        'dashboard',
        'billing',
        'profile',
        'rtl',
        'sign-in',
        'sign-up',
        'tables',
        'virtual-reality',
    }
    if page not in allowed:
        raise Http404("Page not found")
    template_name = f"argon/{page}.html"
    return render(request, template_name)


@login_required
def tables(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'Backoffice/tables.html', { 'users': users })
