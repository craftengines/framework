{#
    Panel — Routes.

    Rendered by `PanelController::routes` at `GET /panel/routes`, behind
    `auth` + `role:admin`.

    The route table *is* the installation's attack surface, so reading it here
    beats grepping `routes/` and hoping nothing registers routes at runtime —
    the CRUD builder does exactly that. The "guard" column is the fast scan: a
    write route with no authorizing middleware is the shape of the `/admin`
    hole that started this work.

    Context:
      rows  list[{methods, uri, name, middleware: list[str], module, guarded}]
#}
@extends("layouts.panel")

@section("title", "Routes")

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                    <th class="px-5 py-3">Method</th>
                    <th class="px-5 py-3">URI</th>
                    <th class="px-5 py-3">Name</th>
                    <th class="px-5 py-3">Middleware</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm">
                @foreach(rows as row)
                    <tr class="hover:bg-slate-50/50">
                        <td class="px-5 py-2.5">
                            <span class="inline-flex px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-100 text-slate-600">{{ row['methods'] }}</span>
                        </td>
                        <td class="px-5 py-2.5 font-mono text-xs text-slate-900">{{ row['uri'] }}</td>
                        <td class="px-5 py-2.5 font-mono text-[11px] text-slate-400">{{ row['name'] }}</td>
                        <td class="px-5 py-2.5">
                            @if(row['middleware']|length > 0)
                                @foreach(row['middleware'] as alias)
                                    <span class="inline-flex px-2 py-0.5 rounded text-[10px] font-semibold font-mono mr-1 mb-0.5
                                        {% if alias.startswith('role:') or alias.startswith('permission:') or alias.startswith('group:') %}bg-orange-50 text-orange-700{% else %}bg-slate-100 text-slate-600{% endif %}">{{ alias }}</span>
                                @endforeach
                            @else
                                <span class="text-[11px] text-slate-400">public</span>
                            @endif
                            @if(row['module'])
                                <span class="inline-flex px-2 py-0.5 rounded text-[10px] font-semibold font-mono bg-indigo-50 text-indigo-700">module:{{ row['module'] }}</span>
                            @endif
                        </td>
                    </tr>
                @endforeach
            </tbody>
        </table>
    </div>
</div>

<p class="text-xs text-slate-500 leading-relaxed">
    Same data as <code class="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">dev.py route list</code>,
    read from the router in this process — including anything registered at runtime.
</p>

@endsection
