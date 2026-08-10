{#
    Panel — Logs.

    Rendered by `PanelController::logs` at `GET /panel/logs`, behind
    `auth` + `role:admin`.

    The last 100 rows of `system_logs`, written by `DatabaseLoggingMiddleware`.
    Columns are taken from the data rather than hardcoded, so a project that
    adds a column to the table sees it here without touching this template —
    and a project that does not use the table at all gets the empty state
    instead of a header row promising data that never comes.

    Context:
      entries  list[dict]
      columns  list[str]  keys of the first entry, or []
#}
@extends("layouts.panel")

@section("title", "Logs")

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    @if(entries|length > 0)
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                        @foreach(columns as column)
                            <th class="px-4 py-3">{{ column }}</th>
                        @endforeach
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                    @foreach(entries as entry)
                        <tr class="hover:bg-slate-50/50">
                            @foreach(columns as column)
                                <td class="px-4 py-2 font-mono text-slate-600 max-w-xs truncate">{{ entry[column] }}</td>
                            @endforeach
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    @else
        <div class="px-5 py-16 text-center">
            <p class="text-sm font-semibold text-slate-900">No entries recorded.</p>
            <p class="text-xs text-slate-500 mt-1">
                Database logging writes to <code class="font-mono">system_logs</code>. File logs live in
                <code class="font-mono">storage/logs</code>.
            </p>
        </div>
    @endif
</div>

@endsection
