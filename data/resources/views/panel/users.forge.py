{#
    Panel — Users.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::users` at
    `GET /panel/users`, behind `auth` + `role:admin`. This is the account
    directory: the same data whose exposure on `/admin` was the security bug
    that started this work, so the guard is not optional and the menu item
    carries the matching `role="admin"` condition.

    Roles and groups per row come from the resolver, so a role inherited
    through a group shows up here exactly as the route middleware sees it.

    Context:
      rows  list[{user, roles: list[str], groups: list[str]}]
#}
@extends("layouts.panel")

@section("title", "Users")

@section("actions")
    <a href="/admin/groups" class="bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold px-5 py-2.5 rounded-xl transition">
        Manage groups
    </a>
@endsection

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                    <th class="px-5 py-3">Account</th>
                    <th class="px-5 py-3">Roles</th>
                    <th class="px-5 py-3">Groups</th>
                    <th class="px-5 py-3">Created</th>
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
                                    <span class="inline-flex px-2 py-0.5 rounded text-[11px] font-semibold bg-orange-50 text-orange-700 font-mono mr-1">{{ role }}</span>
                                @endforeach
                            @else
                                <span class="text-xs text-slate-400">—</span>
                            @endif
                        </td>
                        <td class="px-5 py-3.5">
                            @if(row['groups']|length > 0)
                                @foreach(row['groups'] as group)
                                    <span class="inline-flex px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600 font-mono mr-1">{{ group }}</span>
                                @endforeach
                            @else
                                <span class="text-xs text-slate-400">—</span>
                            @endif
                        </td>
                        <td class="px-5 py-3.5 font-mono text-xs text-slate-400">{{ row['user'].get_attribute('created_at') }}</td>
                    </tr>
                @endforeach
            </tbody>
        </table>
    </div>
</div>

@endsection
