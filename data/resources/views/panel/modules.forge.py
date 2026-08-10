{#
    Panel — Modules.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::modules` at
    `GET /panel/modules`, behind `auth` + `role:admin`. The toggle posts to
    `/panel/modules/toggle`.

    A module is a feature area that can be switched off in the database: a
    route declared with `.module("billing")` answers 404 while its module is
    disabled, with no deploy. That is real power over a running installation,
    which is why this page is admin-only.

    Context:
      modules  list[{slug, name, enabled}]
#}
@extends("layouts.panel")

@section("title", "Modules")

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    @if(modules|length > 0)
        <ul class="divide-y divide-slate-100">
            @foreach(modules as module)
                <li class="flex items-center gap-4 px-5 py-4">
                    <div class="min-w-0 flex-1">
                        <p class="text-sm font-semibold text-slate-900">{{ module['name'] }}</p>
                        <p class="text-xs text-slate-400 font-mono mt-0.5">{{ module['slug'] }}</p>
                    </div>

                    @if(module['enabled'])
                        <span class="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Enabled
                        </span>
                    @else
                        <span class="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg">
                            <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Disabled
                        </span>
                    @endif

                    {# A state change is a POST with CSRF — never a link. A GET
                       that mutates can be triggered by a prefetch, an image tag
                       or a crawler. #}
                    <form action="/panel/modules/toggle" method="POST" class="flex-shrink-0">
                        @csrf
                        <input type="hidden" name="slug" value="{{ module['slug'] }}">
                        <input type="hidden" name="enable" value="{{ '0' if module['enabled'] else '1' }}">
                        <button type="submit" class="text-xs font-bold px-4 py-2 rounded-lg transition
                            {% if module['enabled'] %}text-rose-600 hover:bg-rose-50{% else %}text-white bg-slate-900 hover:bg-slate-800{% endif %}">
                            {{ 'Disable' if module['enabled'] else 'Enable' }}
                        </button>
                    </form>
                </li>
            @endforeach
        </ul>
    @else
        <div class="px-5 py-16 text-center">
            <p class="text-sm font-semibold text-slate-900">No modules registered.</p>
            <p class="text-xs text-slate-500 mt-1">Seed them, or register one with <code class="font-mono">Module.create(...)</code>.</p>
        </div>
    @endif
</div>

<p class="text-xs text-slate-500 leading-relaxed">
    Disabling a module makes every route declared with
    <code class="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">.module("slug")</code>
    answer 404 immediately. The state is cached for a few seconds per process,
    so another worker picks the change up shortly after.
</p>

@endsection
