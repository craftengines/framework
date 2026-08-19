{#
    Panel — My profile.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::profile` at
    `GET /panel/profile`, behind `auth`. Allows authenticated users to view
    their details, update profile information, and rotate passwords securely.

    Context:
      user      User
      is_admin  bool
      request   Request
#}
@extends("layouts.panel")

@section("title", "My profile")

@section("content")

<div class="space-y-6 max-w-4xl">

    {# Flash Notifications #}
    @if(request and request.input('success') == 'profile_updated')
        <div class="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            Your profile details have been successfully updated.
        </div>
    @endif

    @if(request and request.input('success') == 'password_updated')
        <div class="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            Your password has been securely rotated.
        </div>
    @endif

    @if(request and request.input('error') == 'invalid_current_password')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Authentication failed: Current password is incorrect.
        </div>
    @endif

    @if(request and request.input('error') == 'password_mismatch')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Validation failed: New password and confirmation do not match.
        </div>
    @endif

    @if(request and request.input('error') == 'password_too_short')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Security requirement: New password must be at least 8 characters long.
        </div>
    @endif

    @if(request and request.input('error') == 'email_taken')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Conflict: The specified email address is already assigned to another account.
        </div>
    @endif

    @if(request and request.input('error') == 'invalid_email')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Validation failed: Invalid email format or unauthorized domain policy.
        </div>
    @endif

    @if(request and request.input('error') == 'invalid_name')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Validation failed: Full name must contain at least 2 characters.
        </div>
    @endif

    {# Account Identity Overview #}
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div class="flex items-center gap-4 px-6 py-6 border-b border-slate-100">
            <span class="w-14 h-14 rounded-2xl bg-orange-600/10 text-orange-600 flex items-center justify-center text-xl font-black shadow-inner">
                {{ (user.get_attribute('name') or '?')[:1]|upper }}
            </span>
            <div class="min-w-0">
                <p class="text-lg font-extrabold text-slate-900 truncate">{{ user.get_attribute('name') }}</p>
                <p class="text-sm text-slate-500 font-mono truncate">{{ user.get_attribute('email') }}</p>
            </div>
            @if(is_admin)
                <span class="ml-auto px-3 py-1 bg-slate-900 text-white text-xs font-bold font-mono uppercase rounded-lg">
                    Administrator
                </span>
            @endif
        </div>

        <dl class="divide-y divide-slate-100 text-sm bg-slate-50/50">
            <div class="flex px-6 py-3.5 items-center">
                <dt class="w-44 flex-shrink-0 text-slate-500 font-medium">Public Identifier</dt>
                <dd class="font-mono text-xs text-slate-700 break-all">{{ user.get_attribute('uuid') or '—' }}</dd>
            </div>
            <div class="flex px-6 py-3.5 items-center">
                <dt class="w-44 flex-shrink-0 text-slate-500 font-medium">Member Since</dt>
                <dd class="font-mono text-xs text-slate-700">{{ user.get_attribute('created_at') }}</dd>
            </div>
            @if(is_admin)
                <div class="flex px-6 py-3.5 items-center">
                    <dt class="w-44 flex-shrink-0 text-slate-500 font-medium">Account Type</dt>
                    <dd class="font-semibold text-slate-900 font-mono">{{ user.get_attribute('type') or 'standard' }}</dd>
                </div>
                <div class="flex px-6 py-3.5 items-center">
                    <dt class="w-44 flex-shrink-0 text-slate-500 font-medium">Administrator</dt>
                    <dd class="font-semibold text-slate-900">{{ 'yes' if user.get_attribute('is_admin') else 'no' }}</dd>
                </div>
            @endif
        </dl>
    </div>

    {# Self-Service Profile Mutation Form #}
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
        <div class="border-b border-slate-100 pb-4 mb-6">
            <h2 class="text-base font-bold text-slate-900">Personal Information</h2>
            <p class="text-xs text-slate-500 mt-0.5">Update your display name and email address.</p>
        </div>

        <form action="/panel/profile" method="POST" class="space-y-4">
            @csrf
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="space-y-1.5">
                    <label for="name" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Full Name</label>
                    <input type="text" name="name" id="name" required value="{{ user.get_attribute('name') }}"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                </div>
                <div class="space-y-1.5">
                    <label for="email" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Email Address</label>
                    <input type="email" name="email" id="email" required value="{{ user.get_attribute('email') }}"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-mono text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                </div>
            </div>

            <div class="pt-2 flex justify-end">
                <button type="submit" class="bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold px-6 py-2.5 rounded-xl shadow transition">
                    Save Profile Changes
                </button>
            </div>
        </form>
    </div>

    {# Credential Rotation Form #}
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
        <div class="border-b border-slate-100 pb-4 mb-6">
            <h2 class="text-base font-bold text-slate-900">Change Password</h2>
            <p class="text-xs text-slate-500 mt-0.5">Ensure your account uses a strong and unique credential.</p>
        </div>

        <form action="/panel/profile/password" method="POST" class="space-y-4">
            @csrf
            <div class="space-y-1.5">
                <label for="current_password" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Current Password</label>
                <input type="password" name="current_password" id="current_password" required
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="space-y-1.5">
                    <label for="new_password" class="block text-xs font-bold uppercase tracking-wider text-slate-700">New Password</label>
                    <input type="password" name="new_password" id="new_password" required minlength="8"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                </div>
                <div class="space-y-1.5">
                    <label for="new_password_confirmation" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Confirm New Password</label>
                    <input type="password" name="new_password_confirmation" id="new_password_confirmation" required minlength="8"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                </div>
            </div>

            <div class="pt-2 flex justify-end">
                <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white text-sm font-bold px-6 py-2.5 rounded-xl shadow transition">
                    Update Password
                </button>
            </div>
        </form>
    </div>

    {# Administrative Access Audit Navigation #}
    @if(is_admin)
        <div class="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm flex items-center justify-between">
            <div>
                <p class="text-sm font-bold text-slate-900">Security & Access Audit</p>
                <p class="text-xs text-slate-500 mt-0.5">
                    Inspect active roles, groups, ABAC policies, and comprehensive permission resolution trees.
                </p>
            </div>
            <a href="/panel/access" class="bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold px-5 py-2.5 rounded-xl transition shadow">
                Open Access Audit
            </a>
        </div>
    @endif

</div>

@endsection
