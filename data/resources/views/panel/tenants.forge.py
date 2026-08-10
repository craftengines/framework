{#
    Panel — Tenants.

    Rendered by `PanelController::tenants` at `GET /panel/tenants`, behind
    `auth` + `role:admin`.

    Schema-per-tenant isolation needs PostgreSQL. On SQLite and MySQL
    `ensure_tenant_schema` is a documented no-op, which means every tenant
    shares one set of tables — a data-isolation failure wearing the costume of
    a working feature. The banner below says so out loud rather than letting
    the list imply isolation that is not there.

    Context:
      tenants   list      active tenants
      driver    str
      isolated  bool      whether the driver can actually isolate schemas
#}
@extends("layouts.panel")

@section("title", "Tenants")

@section("content")

@if(not isolated)
    <div class="bg-amber-50 border border-amber-200 rounded-2xl p-5">
        <p class="text-sm font-bold text-amber-900">Tenants are not isolated on this driver</p>
        <p class="text-sm text-amber-800 mt-1 leading-relaxed">
            Schema isolation requires PostgreSQL; this installation runs
            <code class="font-mono text-xs">{{ driver }}</code>, so every tenant shares the same tables.
            Use PostgreSQL, or turn off <code class="font-mono text-xs">MULTI_TENANCY_ENABLED</code>
            so the application stops implying an isolation it does not have.
        </p>
    </div>
@endif

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    @if(tenants|length > 0)
        <ul class="divide-y divide-slate-100">
            @foreach(tenants as tenant)
                <li class="flex items-center gap-4 px-5 py-4">
                    <span class="w-9 h-9 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center flex-shrink-0 text-xs font-bold font-mono">T</span>
                    <div class="min-w-0 flex-1 font-mono text-xs text-slate-600 break-all">{{ tenant }}</div>
                    @if(isolated)
                        <span class="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg flex-shrink-0">Isolated schema</span>
                    @else
                        <span class="text-xs font-bold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-lg flex-shrink-0">Shared tables</span>
                    @endif
                </li>
            @endforeach
        </ul>
    @else
        <div class="px-5 py-16 text-center">
            <p class="text-sm font-semibold text-slate-900">No tenants provisioned.</p>
            <p class="text-xs text-slate-500 mt-1">
                An account with <code class="font-mono">type = "tenant"</code> gets its schema created and
                migrated on its first request.
            </p>
        </div>
    @endif
</div>

@endsection
