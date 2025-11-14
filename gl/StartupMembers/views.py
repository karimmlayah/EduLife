from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from Startup.models import Startup
from .models import StartupMember
from django.contrib import messages
from django.contrib.auth.models import User


@login_required
def startup_members(request, startup_id):
    startup = get_object_or_404(Startup, id_startup=startup_id)
    lead = StartupMember.objects.filter(startup=startup, user=request.user, is_lead=True).exists()
    members = StartupMember.objects.filter(startup=startup)

    # send all users (or exclude startup members if you want)
    from django.contrib.auth.models import User
    all_users = User.objects.all()

    return render(request, "startup/Frontoffice/startup_members.html", {
        "startup": startup,
        "members": members,
        "is_lead": lead,
        "users": all_users
    })


@login_required
def add_member(request, startup_id):
    startup = get_object_or_404(Startup, id_startup=startup_id)

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        role = request.POST.get("role", "Member")

        if not user_id:
            return redirect("startup_members", startup_id=startup_id)

        user = User.objects.get(id=user_id)

        # prevent duplicates
        if StartupMember.objects.filter(startup=startup, user=user).exists():
            messages.error(request, "This user is already a member.")
            return redirect("startup_members", startup_id=startup_id)

        StartupMember.objects.create(
            startup=startup,
            user=user,
            role=role,
            is_lead=False
        )

        return redirect("startup_members", startup_id=startup_id)

    return redirect("startup_members", startup_id=startup_id)
@login_required
def delete_member(request, startup_id, member_id):
    startup = get_object_or_404(Startup, id_startup=startup_id)
    member = get_object_or_404(StartupMember, id_member=member_id)

    # Only lead can delete, and cannot delete lead
    if not StartupMember.objects.filter(startup=startup, user=request.user, is_lead=True).exists():
        return redirect("startup_members", startup_id=startup_id)

    if member.is_lead:
        return redirect("startup_members", startup_id=startup_id)

    member.delete()
    return redirect("startup_members", startup_id=startup_id)
@login_required
def edit_member(request, startup_id, member_id):
    startup = get_object_or_404(Startup, id_startup=startup_id)
    member = get_object_or_404(StartupMember, id_member=member_id)

    # Only the founder can edit (not members)
    if not StartupMember.objects.filter(startup=startup, user=request.user, is_lead=True).exists():
        return redirect("startup_members", startup_id=startup_id)

    if request.method == "POST":
        role = request.POST.get("role", "").strip()

        if role:
            member.role = role

        member.save()

    return redirect("startup_members", startup_id=startup_id)
