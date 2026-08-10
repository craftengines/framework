{#
    Panel — My profile.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::profile` at
    `GET /panel/profile`, behind `auth`. Shows the visitor's own account only.

    Read-only for now, and deliberately so: there is no profile-update action
    in the framework yet, and rendering a form that posts nowhere would be the
    exact kind of placebo this codebase removes on sight. What is missing is
    stated on the page instead.

    Context:
      user  User
#}
@extends("layouts.panel")

@section("title", "My profile")

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    <div class="flex items-center gap-4 px-6 py-6 border-b border-slate-100">
        <span class="w-14 h-14 rounded-2xl bg-orange-600/10 text-orange-600 flex items-center justify-center text-xl font-black">
            {{ (user.get_attribute('name') or '?')[:1]|upper }}
        </span>
        <div class="min-w-0">
            <p class="text-lg font-extrabold text-slate-900 truncate">{{ user.get_attribute('name') }}</p>
            <p class="text-sm text-slate-500 font-mono truncate">{{ user.get_attribute('email') }}</p>
        </div>
    </div>

    <dl class="divide-y divide-slate-100 text-sm">
        <div class="flex px-6 py-3.5">
            <dt class="w-40 flex-shrink-0 text-slate-500">Public identifier</dt>
            <dd class="font-mono text-xs text-slate-600 break-all">{{ user.get_attribute('uuid') or '—' }}</dd>
        </div>
        <div class="flex px-6 py-3.5">
            <dt class="w-40 flex-shrink-0 text-slate-500">Member since</dt>
            <dd class="font-mono text-xs text-slate-600">{{ user.get_attribute('created_at') }}</dd>
        </div>

        {# Security-shaped metadata — the internal account `type` and the
           administrator flag — is shown to administrators only. To an ordinary
           visitor this page is their name, their email and when they joined:
           their own data, never a description of how access is configured. #}
        @if(is_admin)
            <div class="flex px-6 py-3.5">
                <dt class="w-40 flex-shrink-0 text-slate-500">Account type</dt>
                <dd class="font-semibold text-slate-900 font-mono">{{ user.get_attribute('type') or 'user' }}</dd>
            </div>
            <div class="flex px-6 py-3.5">
                <dt class="w-40 flex-shrink-0 text-slate-500">Administrator</dt>
                <dd class="font-semibold text-slate-900">{{ 'yes' if user.get_attribute('is_admin') else 'no' }}</dd>
            </div>
        @endif
    </dl>
</div>

<div class="bg-amber-50 border border-amber-200 rounded-2xl p-5">
    <p class="text-sm font-bold text-amber-900">Editing your profile is not built yet</p>
    <p class="text-sm text-amber-800 mt-1 leading-relaxed">
        Craft has no profile-update action, and no password-reset flow — that one
        needs the mail subsystem, which does not exist either. This page shows
        what the account actually is rather than a form that would post nowhere.
        See <code class="font-mono text-xs">CRAFT_ENGINE.md</code> for the full
        list of what is not built.
    </p>
</div>

{# The link to the access audit is administrators-only, and so is the audit
   itself: it lists permission slugs, the path each grant arrives by and the
   raw ABAC conditions — how the installation is secured, not what this person
   is. Offering it here to everyone was the leak. #}
@if(is_admin)
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-sm font-bold text-slate-900">Access audit</p>
        <p class="text-sm text-slate-500 mt-1 mb-3">
            Roles, groups and every permission grant — with the path each one arrives by.
        </p>
        <a href="/panel/access" class="inline-block bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold px-5 py-2.5 rounded-xl transition">
            Open the audit
        </a>
    </div>
@endif

@endsection
