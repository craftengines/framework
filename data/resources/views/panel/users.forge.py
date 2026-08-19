{#
    Panel — Users & RBAC Management.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::users` at
    `GET /panel/users`, behind `auth` + `role:admin`. Enables administrators
    to provision users (including demo/test accounts) and manage role/group assignments.

    Context:
      rows    list[{user, roles: list[str], groups: list[str]}]
      roles   list[Role]
      groups  list[Group]
      request Request
#}
@extends("layouts.panel")

@section("title", "Users")

@section("actions")
    <div class="flex items-center gap-3">
        <a href="/admin/roles" class="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-bold px-4 py-2.5 rounded-xl transition shadow-sm">
            Manage Roles
        </a>
        <a href="/admin/groups" class="bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold px-4 py-2.5 rounded-xl transition shadow-sm">
            Manage Groups
        </a>
    </div>
@endsection

@section("content")

<div class="space-y-6">

    {# Flash Notifications #}
    @if(request and request.input('success') == 'user_created')
        <div class="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            User entity provisioned successfully.
        </div>
    @endif

    @if(request and request.input('success') == 'role_assigned')
        <div class="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            Role granted to user account.
        </div>
    @endif

    @if(request and request.input('success') == 'role_revoked')
        <div class="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            Role successfully revoked.
        </div>
    @endif

    @if(request and request.input('success') == 'group_assigned')
        <div class="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            User added to group successfully.
        </div>
    @endif

    @if(request and request.input('success') == 'group_revoked')
        <div class="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            User removed from group.
        </div>
    @endif

    @if(request and request.input('error') == 'email_taken')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Cannot provision account: Email address already registered.
        </div>
    @endif

    @if(request and request.input('error') == 'missing_fields')
        <div class="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-medium flex items-center gap-3 shadow-sm">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Provisioning error: Name, email, and password are required.
        </div>
    @endif

    {# Provision User Card #}
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
        <div class="border-b border-slate-100 pb-4 mb-6">
            <h2 class="text-base font-bold text-slate-900">Provision User Account</h2>
            <p class="text-xs text-slate-500 mt-0.5">Create administrative, standard, demo, or operational user entities.</p>
        </div>

        <form action="/panel/users" method="POST" class="space-y-4">
            @csrf
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="space-y-1.5">
                    <label for="new_name" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Full Name</label>
                    <input type="text" name="name" id="new_name" required placeholder="Jane Doe"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                </div>
                <div class="space-y-1.5">
                    <label for="new_email" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Email</label>
                    <input type="email" name="email" id="new_email" required placeholder="user@craft.local"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-mono text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                </div>
                <div class="space-y-1.5">
                    <label for="new_password" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Password</label>
                    <input type="password" name="password" id="new_password" required minlength="8" placeholder="••••••••••••"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                <div class="space-y-1.5">
                    <label for="new_role_id" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Initial Role (Optional)</label>
                    <select name="role_id" id="new_role_id"
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                        <option value="">— None —</option>
                        @foreach(roles as role)
                            <option value="{{ role.get_attribute('id') }}">{{ role.get_attribute('name') }} ({{ role.get_attribute('slug') }})</option>
                        @endforeach
                    </select>
                </div>
                <div class="space-y-1.5">
                    <label for="new_group_id" class="block text-xs font-bold uppercase tracking-wider text-slate-700">Initial Group (Optional)</label>
                    <select name="group_id" id="new_group_id"
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition">
                        <option value="">— None —</option>
                        @foreach(groups as group)
                            <option value="{{ group.get_attribute('id') }}">{{ group.get_attribute('name') }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="flex items-center justify-between gap-4 py-2">
                    <label class="flex items-center gap-2 cursor-pointer text-sm font-semibold text-slate-700">
                        <input type="checkbox" name="is_admin" value="1" class="rounded border-slate-300 text-orange-600 focus:ring-orange-500">
                        <span>Grant Admin Flag</span>
                    </label>
                    <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white text-sm font-bold px-6 py-2.5 rounded-xl shadow transition">
                        Create Account
                    </button>
                </div>
            </div>
        </form>
    </div>

    {# Directory Table #}
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                        <th class="px-5 py-3">Account</th>
                        <th class="px-5 py-3">Roles</th>
                        <th class="px-5 py-3">Groups</th>
                        <th class="px-5 py-3">Created</th>
                        <th class="px-5 py-3 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm">
                    @foreach(rows as row)
                        <tr class="hover:bg-slate-50/50">
                            <td class="px-5 py-3.5">
                                <div class="flex items-center gap-3">
                                    <span class="w-8 h-8 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center text-xs font-bold flex-shrink-0">
                                        {{ (row['user'].get_attribute('name') or '?')[:1]|upper }}
                                    </span>
                                    <div class="min-w-0">
                                        <p class="font-semibold text-slate-900 truncate">{{ row['user'].get_attribute('name') }}</p>
                                        <p class="text-xs text-slate-500 font-mono truncate">{{ row['user'].get_attribute('email') }}</p>
                                    </div>
                                    @if(row['user'].get_attribute('is_admin'))
                                        <span class="ml-1 text-[10px] font-bold uppercase bg-slate-900 text-white px-1.5 py-0.5 rounded">admin</span>
                                    @endif
                                </div>
                            </td>
                            <td class="px-5 py-3.5">
                                @if(row['roles']|length > 0)
                                    @foreach(row['roles'] as role)
                                        <span class="inline-flex px-2 py-0.5 rounded text-[11px] font-semibold bg-orange-50 text-orange-700 font-mono mr-1 mb-1">{{ role }}</span>
                                    @endforeach
                                @else
                                    <span class="text-xs text-slate-400">—</span>
                                @endif
                            </td>
                            <td class="px-5 py-3.5">
                                @if(row['groups']|length > 0)
                                    @foreach(row['groups'] as group)
                                        <span class="inline-flex px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600 font-mono mr-1 mb-1">{{ group }}</span>
                                    @endforeach
                                @else
                                    <span class="text-xs text-slate-400">—</span>
                                @endif
                            </td>
                            <td class="px-5 py-3.5 font-mono text-xs text-slate-400">{{ row['user'].get_attribute('created_at') }}</td>
                            <td class="px-5 py-3.5 text-right">
                                <details class="relative inline-block text-left">
                                    <summary class="list-none cursor-pointer px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold">
                                        Manage
                                    </summary>
                                    <div class="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-slate-200 p-4 z-50 text-left space-y-4">
                                        {# Quick Assign Role #}
                                        <form action="/panel/users/roles/assign" method="POST" class="space-y-1.5">
                                            @csrf
                                            <input type="hidden" name="user_id" value="{{ row['user'].get_attribute('id') }}">
                                            <label class="block text-[10px] font-bold uppercase text-slate-500">Grant Role</label>
                                            <div class="flex gap-1.5">
                                                <select name="role_id" class="w-full text-xs px-2 py-1.5 rounded-lg border border-slate-200">
                                                    @foreach(roles as role)
                                                        <option value="{{ role.get_attribute('id') }}">{{ role.get_attribute('name') }}</option>
                                                    @endforeach
                                                </select>
                                                <button type="submit" class="px-2.5 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800">
                                                    +
                                                </button>
                                            </div>
                                        </form>

                                        {# Quick Assign Group #}
                                        <form action="/panel/users/groups/assign" method="POST" class="space-y-1.5 border-t border-slate-100 pt-3">
                                            @csrf
                                            <input type="hidden" name="user_id" value="{{ row['user'].get_attribute('id') }}">
                                            <label class="block text-[10px] font-bold uppercase text-slate-500">Add to Group</label>
                                            <div class="flex gap-1.5">
                                                <select name="group_id" class="w-full text-xs px-2 py-1.5 rounded-lg border border-slate-200">
                                                    @foreach(groups as group)
                                                        <option value="{{ group.get_attribute('id') }}">{{ group.get_attribute('name') }}</option>
                                                    @endforeach
                                                </select>
                                                <button type="submit" class="px-2.5 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800">
                                                    +
                                                </button>
                                            </div>
                                        </form>
                                    </div>
                                </details>
                            </td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    </div>

</div>

@endsection
