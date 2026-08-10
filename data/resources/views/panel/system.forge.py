{#
    Panel — About this install.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::system` at
    `GET /panel/system`, behind `auth` + `role:admin`.

    Every value is read from the *running* application — the resolved config,
    the live database driver, the interpreter actually executing — rather than
    from a config file that may not be the one in effect. That distinction is
    the whole point of the page: it answers "what is this process really doing"
    during an incident, and admin-only because it names versions and platform.

    Context:
      facts  list[(label, value)]
#}
@extends("layouts.panel")

@section("title", "About this install")

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    <dl class="divide-y divide-slate-100 text-sm">
        @foreach(facts as fact)
            <div class="flex px-6 py-3.5">
                <dt class="w-48 flex-shrink-0 text-slate-500">{{ fact[0] }}</dt>
                <dd class="font-semibold text-slate-900 font-mono text-xs break-all">{{ fact[1] }}</dd>
            </div>
        @endforeach
    </dl>
</div>

<div class="grid gap-4 sm:grid-cols-2">
    <a href="/admin/crud-builder" class="block bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:border-orange-300 transition">
        <p class="text-sm font-bold text-slate-900">CRUD builder</p>
        <p class="text-xs text-slate-500 mt-1 leading-relaxed">
            Generate a migration, model, request, resource, JSON API and admin UI
            for an entity. Writes real files — hence admin-only.
        </p>
    </a>
    <a href="/docs" class="block bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:border-orange-300 transition">
        <p class="text-sm font-bold text-slate-900">Documentation</p>
        <p class="text-xs text-slate-500 mt-1 leading-relaxed">
            The framework reference: routing, the ORM, migrations, authorization,
            queues, deployment.
        </p>
    </a>
</div>

@endsection
