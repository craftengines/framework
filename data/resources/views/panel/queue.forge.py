{#
    Panel — Queue.

    Rendered by `PanelController::queue` at `GET /panel/queue`, behind
    `auth` + `role:admin`.

    Counts come from the `jobs` table. A count of `None` renders as "—": the
    table not existing (nothing has ever been queued here) is not the same
    fact as "zero jobs waiting", and a dashboard that conflates them is how an
    unprocessed backlog looks healthy.

    Context:
      connection  str   the configured queue driver
      pending     int|None
      attempted   int|None   jobs that have been tried at least once
      recent      list[{id, queue, attempts, available_at}]
#}
@extends("layouts.panel")

@section("title", "Queue")

@section("content")

<div class="grid gap-4 sm:grid-cols-3">
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Connection</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 font-mono">{{ connection }}</p>
    </div>
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Waiting</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 tabular-nums">{{ pending if pending is not none else '—' }}</p>
    </div>
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400">Retried</p>
        <p class="mt-2 text-2xl font-extrabold text-slate-900 tabular-nums">{{ attempted if attempted is not none else '—' }}</p>
        <p class="mt-1 text-xs text-slate-500">Attempted at least once</p>
    </div>
</div>

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    @if(recent|length > 0)
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                        <th class="px-5 py-3">#</th>
                        <th class="px-5 py-3">Queue</th>
                        <th class="px-5 py-3">Attempts</th>
                        <th class="px-5 py-3">Available at</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm">
                    @foreach(recent as job)
                        <tr>
                            <td class="px-5 py-2.5 font-mono text-xs text-slate-400">{{ job['id'] }}</td>
                            <td class="px-5 py-2.5 font-mono text-xs text-slate-900">{{ job['queue'] }}</td>
                            <td class="px-5 py-2.5 font-mono text-xs tabular-nums {% if job['attempts'] %}text-amber-600 font-bold{% else %}text-slate-500{% endif %}">{{ job['attempts'] }}</td>
                            <td class="px-5 py-2.5 font-mono text-[11px] text-slate-400">{{ job['available_at'] }}</td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    @else
        <div class="px-5 py-16 text-center">
            <p class="text-sm font-semibold text-slate-900">Nothing queued.</p>
            <p class="text-xs text-slate-500 mt-1">
                Push a job with <code class="font-mono">Queue.push(...)</code> and process it with
                <code class="font-mono">dev.py queue work</code>.
            </p>
        </div>
    @endif
</div>

<p class="text-xs text-slate-500 leading-relaxed">
    Jobs are serialised as JSON, never pickle, so a worker in another process
    can rebuild them. <code class="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">QUEUE_CONNECTION=redis</code>
    is not implemented — it warns and falls back to <code class="font-mono">database</code>.
</p>

@endsection
