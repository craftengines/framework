{#
    Panel — Database.

    Rendered by `PanelController::database` at `GET /panel/database`, behind
    `auth` + `role:admin`.

    Driver, connection pool and every table with its row count, read from the
    live connection. The pool figures are the ones that matter under load:
    `open` is how many physical connections this worker holds, capped by
    `pool_size`, and the total across the server is `pool_size × workers`
    against the database's own `max_connections`.

    A table whose count could not be read shows "—", never 0: "no rows" and
    "could not ask" mean opposite things.

    Context:
      driver, pool: {open, idle}, pool_size, tables: [{name, rows}]
#}
@extends("layouts.panel")

@section("title", "Database")

@section("content")

<div class="grid gap-4 sm:grid-cols-3">
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Driver</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 font-mono">{{ driver }}</p>
    </div>
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Pool in use</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 tabular-nums">{{ pool['open'] }} / {{ pool_size }}</p>
        <p class="mt-1 text-xs text-slate-500">{{ pool['idle'] }} idle — per worker process</p>
    </div>
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Tables</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 tabular-nums">{{ tables|length }}</p>
    </div>
</div>

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                    <th class="px-5 py-3">Table</th>
                    <th class="px-5 py-3 text-right">Rows</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm">
                @foreach(tables as table)
                    <tr class="hover:bg-slate-50/50">
                        <td class="px-5 py-2.5 font-mono text-xs text-slate-900">{{ table['name'] }}</td>
                        <td class="px-5 py-2.5 text-right font-mono text-xs tabular-nums text-slate-600">
                            {# "—" means the count could not be read, not zero. #}
                            {{ table['rows'] if table['rows'] is not none else '—' }}
                        </td>
                    </tr>
                @endforeach
            </tbody>
        </table>
    </div>
</div>

@endsection
