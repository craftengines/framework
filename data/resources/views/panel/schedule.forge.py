{#
    Panel — Scheduler.

    Rendered by `PanelController::schedule` at `GET /panel/schedule`, behind
    `auth` + `role:admin`.

    Tasks registered in `routes/console.py` and their cron expressions, read
    from the live scheduler. Read-only: running a task from a browser session
    would execute application code on demand, and the CLI
    (`dev.py schedule run`) is the deliberate, auditable path for that.

    Context:
      rows  list[{name, expression}]
#}
@extends("layouts.panel")

@section("title", "Scheduler")

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    @if(rows|length > 0)
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                    <th class="px-5 py-3">Task</th>
                    <th class="px-5 py-3">Runs</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm">
                @foreach(rows as row)
                    <tr>
                        <td class="px-5 py-3 font-semibold text-slate-900">{{ row['name'] }}</td>
                        <td class="px-5 py-3 font-mono text-xs text-slate-500">{{ row['expression'] }}</td>
                    </tr>
                @endforeach
            </tbody>
        </table>
    @else
        <div class="px-5 py-16 text-center">
            <p class="text-sm font-semibold text-slate-900">Nothing scheduled.</p>
            <p class="text-xs text-slate-500 mt-1">
                Register tasks in <code class="font-mono">routes/console.py</code> with
                <code class="font-mono">Schedule.call(...)</code>.
            </p>
        </div>
    @endif
</div>

<p class="text-xs text-slate-500 leading-relaxed">
    Run them with <code class="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">dev.py schedule work</code>
    in the foreground, or point cron at
    <code class="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">dev.py schedule run</code> every minute.
    Overlapping runs are prevented by a lock.
</p>

@endsection
