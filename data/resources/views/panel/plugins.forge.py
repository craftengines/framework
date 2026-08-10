{#
    Panel — Plugins.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::plugins` at
    `GET /panel/plugins`, behind `auth` + `role:admin`.

    Plugins are discovered from `plugins/<slug>/plugin.py`, each exposing a
    `PLUGIN` dict, and their enabled state is persisted. Read-only here on
    purpose: enabling a plugin runs third-party code, and the CLI
    (`dev.py plugin enable <slug>`) is the deliberate, auditable path for that.
    A one-click button in a browser session is not the right affordance for it.

    Context:
      plugins  list[dict]  as returned by PluginManager.installed()
#}
@extends("layouts.panel")

@section("title", "Plugins")

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    @if(plugins|length > 0)
        <ul class="divide-y divide-slate-100">
            @foreach(plugins as plugin)
                <li class="flex items-center gap-4 px-5 py-4">
                    <span class="w-9 h-9 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center flex-shrink-0">
                        {{ panel_icon('puzzle')|safe }}
                    </span>
                    <div class="min-w-0 flex-1">
                        <p class="text-sm font-semibold text-slate-900">{{ plugin['name'] if 'name' in plugin else plugin['slug'] }}</p>
                        <p class="text-xs text-slate-400 font-mono mt-0.5">{{ plugin['slug'] }}</p>
                    </div>
                    @if(plugin['enabled'])
                        <span class="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Enabled
                        </span>
                    @else
                        <span class="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg">
                            <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Disabled
                        </span>
                    @endif
                </li>
            @endforeach
        </ul>
    @else
        <div class="px-5 py-16 text-center">
            <p class="text-sm font-semibold text-slate-900">No plugins installed.</p>
            <p class="text-xs text-slate-500 mt-1">
                Drop one in <code class="font-mono">plugins/&lt;slug&gt;/plugin.py</code> and run
                <code class="font-mono">dev.py plugin sync</code>.
            </p>
        </div>
    @endif
</div>

<p class="text-xs text-slate-500 leading-relaxed">
    Enabling a plugin runs third-party code, so it is done from the CLI —
    <code class="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">dev.py plugin enable &lt;slug&gt;</code> —
    not from a browser session.
</p>

@endsection
