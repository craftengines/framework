{#
    Admin — Permissions.

    Rendered by `app/Http/Controllers/Admin/RoleController.py::PermissionController.index`
    at `GET /admin/permissions`, behind `auth` + `role:admin`. Read-only: a
    permission is created by `dev.py permission create`, or by whatever grants
    it — this page is the catalogue.

    Context:
      permissions   list[Permission]
      show_sidebar  bool
#}
@extends("layouts.app")

@section("title", "Permissions — Admin")

@section("content")
<div class="space-y-8">
    <div>
        <h1 class="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">Permissions</h1>
        <p class="text-slate-500 text-sm mt-1">Every permission slug known to the RBAC system.</p>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-xs font-bold uppercase text-slate-500 font-mono">
                        <th class="px-6 py-3.5">Name</th>
                        <th class="px-6 py-3.5">Slug</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
                    @foreach(permissions as permission)
                        <tr>
                            <td class="px-6 py-4 font-semibold text-slate-900">{{ permission.get_attribute('name') }}</td>
                            <td class="px-6 py-4 font-mono text-xs text-slate-500">{{ permission.get_attribute('slug') }}</td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    </div>

    <a href="/admin/roles" class="text-sm font-semibold text-slate-500 hover:text-slate-700">&larr; Back to Roles</a>
</div>
@endsection
